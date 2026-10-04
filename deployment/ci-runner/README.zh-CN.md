# 自建 CI runner

[English](README.md) | [简体中文](README.zh-CN.md)

`.github/workflows/ci.yml` 里的所有任务都在 staging VPS 上的这台 runner 上运行，而不是 GitHub 托管的机器。
GitHub 免费版的私有仓库每月只有 2,000 分钟 Actions 额度。2026-10-04 额度用完：四天跑了 145 次，每次约 13 个计费分钟。
自建 runner 的运行时间不计费。

## 与线上环境的隔离

这台 VPS 同时运行着 SecureView 本身：API 在 `127.0.0.1:8000`，MySQL 在 `127.0.0.1:3306`。
CI 用的是同样的端口，而且会运行每个 PR 的代码，以及几百个 npm 和 pip 包。所以 runner 从不直接接触宿主机。

| 方面 | 做法 |
| --- | --- |
| 任务启动的容器（MySQL 服务、篡改实验室） | 运行在 runner 专用的 Docker（`dind`）里，看不到宿主机的容器、镜像、卷和端口。不挂载宿主机的 Docker socket。 |
| 端口 | runner 只和 dind 共用网络命名空间。任务发布在 3306 的服务，对该任务来说就是 `127.0.0.1:3306`，和宿主机的 3306 无关。 |
| 访问宿主机 | `mcs21-ci-runner-firewall.service` 阻止 CI 网段 `172.31.250.0/24` 主动连接宿主机自身的任何地址：sshd、Docker 网桥上的微信机器人、MySQL。外网访问保持开放（GitHub、npm、PyPI、Docker Hub）。 |
| 负载 | dind 最多 2.5 核、5 GB；runner 最多 3 核、5 GB。在 8 核 15 GB 的机器上给线上留出余量。 |
| 密钥 | 不挂载 `/opt/mcs21`、`/run/secrets`、`/etc` 中的任何内容。唯一的状态是三个命名卷。 |

**剩余风险：** dind 需要 `privileged: true`，所以如果 CI 里有恶意依赖包、并且逃逸出容器，就能到达宿主机。
之所以接受这一风险，是因为仓库是私有的，只有团队 5 人能推送代码。如果情况改变（例如仓库改为公开），先停掉 runner。

## 安装或更新（在 VPS 上以 root 运行）

1. 由仓库 **admin** 生成注册令牌（一小时内有效），在 **Settings → Actions → Runners → New self-hosted runner** 里生成，或者运行：

   ```bash
   gh api -X POST repos/jsonrar/fyp-secure-file-platform/actions/runners/registration-token --jq .token
   ```

2. 在 VPS 上进入本目录运行：

   ```bash
   bash install.sh
   ```

   只有第一次会要求输入令牌。脚本会把文件复制到 `/opt/mcs21-ci-runner`，启用防火墙 unit，构建镜像并启动两个容器。
   然后检查隔离是否生效：必须能访问 GitHub，并且必须无法访问 `172.17.0.1:8112`、宿主机的 sshd 和 `127.0.0.1:3306`。
3. **Settings → Actions → Runners** 里应显示 `mcs21-vps` 为 *Idle*。

再次运行 `install.sh` 会更新 runner，并保留已有的注册。

## 日常运维

```bash
cd /opt/mcs21-ci-runner
docker compose ps                     # 两个容器都是 Up
docker compose logs --tail 50 runner  # "Listening for Jobs"、任务开始和结束
docker compose restart                # dind 重启后还需要：docker compose up -d --force-recreate runner
docker compose down                   # 停掉 CI；恢复之前任务会在 GitHub 上排队
```

- 只有一台 runner，所以任务逐个运行。一次完整 CI 约 15–20 分钟，而 GitHub 并行机器上约 5 分钟。
- 想退回 GitHub 托管机器，把 `ci.yml` 中的 `runs-on: [self-hosted, mcs21-ci]` 改回 `ubuntu-latest`。这只在 GitHub 还有剩余分钟时有用。
- dind 的卷会保留拉取过的镜像（MySQL、篡改实验室）。磁盘满了就清理：
  `docker compose exec dind docker system prune -af`。
