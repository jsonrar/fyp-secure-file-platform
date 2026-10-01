# 预发布环境自动部署

[English](AUTOMATIC_DEPLOYMENT.md) | [简体中文](AUTOMATIC_DEPLOYMENT.zh-CN.md)

MCS21 预发布 VPS 会在新提交合并到 GitHub `main` **并通过 CI** 后自动部署。由 root 管理的 systemd timer
约每两分钟检查一次私有仓库，并把准确的 commit SHA 交给现有、带保护措施的
`mcs21-deploy` 发布命令。团队成员仍按“分支开发、Pull Request 评审、合并 `main`”协作，
不需要共享服务器账户或 Deploy Key。

当前采用服务器主动拉取。GitHub Actions 不负责部署任何东西，它唯一的作用是移动 `deploy` 分支来标记
某个提交是安全的（见[CI 门禁](#ci-门禁)）。只读 Repository Deploy Key 仅保存在 VPS
的专用 `mcs21-deploy` 服务账户中；GitHub 不保存 VPS SSH 私钥或生产 Secret。

## 发布流程与保护措施

```text
开发分支 -> Pull Request -> 合并 main -> 该 commit 通过 CI
         -> CI 把 `deploy` 分支移动到它
         -> systemd timer 拉取 `deploy` -> 部署准确 commit
         -> 数据库备份及只读核验
         -> 构建与预检 -> 原子切换 release
         -> 重启服务及健康检查 -> 写入审计记录
```

底层发布命令会锁定并串行执行部署、保留上一版本，并在切换后的健康检查失败时回滚应用。
自动数据库步骤只包括备份和生产 SQL 只读核验。运行账户不能修改 Schema，自动部署服务也
没有 MySQL 管理员或迁移凭据。因此，Schema 变化必须按照
[DEPLOYMENT.zh-CN.md](DEPLOYMENT.zh-CN.md) 单独提供并评审 DBA SQL 发布，并且必须在推送依赖
它的代码**之前**先应用到数据库——先推代码会导致部署中止并隔离该 SHA，之后的每一个提交都会卡在
它后面。参见
[对运行中的部署应用 Schema Revision](DEPLOYMENT.zh-CN.md#对运行中的部署应用-schema-revision)。

核验器会区分全新审计链（`OK`）与已经包含应用事件、但状态一致的在线审计链
（`LIVE_DATA`）。在线状态只有在单例链头保留准确的发布 Schema 标记、指向最新审计记录，
且哈希与该记录一致时才会通过；`REVIEW`、`MISSING` 和 `UNEXPECTED` 仍会阻止部署。这样
代码发布不会把正常保留的审计证据误判为 Schema 漂移，同时不会削弱数据库、账户、授权与
结构核验。

如果某个 commit 部署失败，该 SHA 会进入隔离状态。Timer 不会反复部署同一个坏版本；
只有 `main` 出现新 commit，或管理员完成排查后显式清除隔离，才会再次尝试。定时检查再次
遇到同一隔离 SHA 时，会记录跳过并以成功状态退出：原始失败证据仍保留，但 systemd 不会
每两分钟重复产生一条新失败。

## CI 门禁

在 `promote` 作业出现之前，timer 会部署 `main` 上的任何内容：直接推送，或 CI 为红的合并，都会在约两分钟内进入
生产环境（威胁模型发现 F-01）。通常的办法是 GitHub 分支保护，但仓库是免费套餐下的私有仓库，无法使用，所以
门禁用一个分支来实现。

- `.github/workflows/ci.yml` 中的 `promote` 作业只在推送到 `main` 时运行，并且要等 `backend`、`frontend`、
  `mysql-gate`、`e2e-live`、`tamper-drill` 在该 commit 上**全部**通过之后才运行。它通过 GitHub REST API 把
  `deploy` 分支移动到该 commit。该分支只会**向前**移动：较旧的一次运行晚结束也无法把它拉回去；历史分叉时
  作业会失败，而不是强制覆盖任何东西。
- timer 同时拉取 `main` 与 `deploy`，并部署 `deploy` 的 commit。发布命令仍要求该 commit 可从 `main` 到达，
  而它总是满足这一点。
- CI 为红的 commit 根本不会被推进，下一个绿色 commit 会包含它。代价是延迟：现在合并后要等 CI 结束（约五分钟）
  再加最多两分钟的 timer，而不是两分钟。
- 在 CI 推进过任何 commit 之前，timer 会报告 `deploy` 不存在并且什么都不部署，同时不产生失败的 unit（失败即关闭）。
- timer 绝不会把 release 往回退：如果手动执行 `mcs21-deploy all main` 让服务器领先于 `deploy`，定时检查会保持不动。
- `sudo mcs21-auto-deploy status` 会同时输出 `cached_deploy`（允许上线的版本）和 `cached_main`（已合并的版本）；
  两者不同说明 CI 还在跑或是红的。

门禁**不**做什么。它不要求评审：任何有推送权限的人仍可把 commit 放到 `main`，只要通过 CI 就会部署。它也不会阻止
管理员执行 `sudo mcs21-deploy all main`，这是有意保留的手动应急入口，会绕过 CI 部署。另外，若 `main` 被强制推送，
使 `deploy` 不再是其祖先，`promote` 会以“diverged”失败；修复办法是把 `deploy` 指向 `main` 上已知良好的 commit
（`gh api --method PATCH repos/jsonrar/fyp-secure-file-platform/git/refs/heads/deploy -f sha=<sha> -F force=true`），
这需要写权限，属于管理员的决定。

## 日常运维命令

获得部署权限的队员都可以查看状态和记录：

```bash
sudo mcs21-auto-deploy status
systemctl status mcs21-auto-deploy.timer --no-pager
journalctl -u mcs21-auto-deploy.service --no-pager -n 100
sudo mcs21-deploy history
```

修复临时故障后，清除隔离并重新部署当前通过 CI 的 commit：

```bash
sudo mcs21-auto-deploy retry
```

管理员也可以强制执行一次验证，或继续使用手动发布入口：

```bash
sudo mcs21-auto-deploy force
sudo mcs21-deploy all
```

## 安装文件

仓库中的版本化参考文件位于 `deployment/server/`。预发布 VPS 上的安装位置为：

- `mcs21-deploy` -> `/usr/local/sbin/mcs21-deploy`，是手动与自动发布共用的保护流程实现；
- `mcs21-auto-deploy` -> `/usr/local/sbin/mcs21-auto-deploy`，由 root 持有，部署队员不可修改；
- `mcs21-auto-deploy.service` 和 `mcs21-auto-deploy.timer` -> `/etc/systemd/system/`。

服务器还单独保存环境专用的 Git mirror、Deploy Key、Secret、备份与 sudo policy；这些
环境专用内容不得复制进 Git。

启用 timer：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mcs21-auto-deploy.timer
```

如果以后让 GitHub Actions 自己执行部署，而不只是标记 commit，仍需要取得仓库管理权限、使用受保护的部署环境
Secret，并单独评审凭据方案。绝不能把 VPS 私钥提交到仓库或直接写进 workflow。
