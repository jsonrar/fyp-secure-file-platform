# 预发布环境自动部署

[English](AUTOMATIC_DEPLOYMENT.md) | [简体中文](AUTOMATIC_DEPLOYMENT.zh-CN.md)

MCS21 预发布 VPS 会在新提交合并到 GitHub `main` 后自动部署。由 root 管理的 systemd timer
约每两分钟检查一次私有仓库，并把准确的 commit SHA 交给现有、带保护措施的
`mcs21-deploy` 发布命令。团队成员仍按“分支开发、Pull Request 评审、合并 `main`”协作，
不需要共享服务器账户或 Deploy Key。

当前采用服务器主动拉取，不是 GitHub Actions。只读 Repository Deploy Key 仅保存在 VPS
的专用 `mcs21-deploy` 服务账户中；GitHub 不保存 VPS SSH 私钥或生产 Secret。

## 发布流程与保护措施

```text
开发分支 -> Pull Request -> 合并 main
         -> systemd timer 拉取 main -> 部署准确 commit
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

如果某个 `main` commit 部署失败，该 SHA 会进入隔离状态。Timer 不会反复部署同一个坏版本；
只有 `main` 出现新 commit，或管理员完成排查后显式清除隔离，才会再次尝试。定时检查再次
遇到同一隔离 SHA 时，会记录跳过并以成功状态退出：原始失败证据仍保留，但 systemd 不会
每两分钟重复产生一条新失败。

## 日常运维命令

获得部署权限的队员都可以查看状态和记录：

```bash
sudo mcs21-auto-deploy status
systemctl status mcs21-auto-deploy.timer --no-pager
journalctl -u mcs21-auto-deploy.service --no-pager -n 100
sudo mcs21-deploy history
```

修复临时故障后，清除隔离并重新部署当前 `main`：

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

以后迁移到 GitHub Actions 前，需要取得仓库管理权限、使用受保护的部署环境 Secret、建立
强制测试关卡，并单独评审凭据方案。绝不能把 VPS 私钥提交到仓库或直接写进 workflow。
