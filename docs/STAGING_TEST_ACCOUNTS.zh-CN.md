# Staging 测试账号

[English](STAGING_TEST_ACCOUNTS.md) | [简体中文](STAGING_TEST_ACCOUNTS.zh-CN.md)

本说明用于在 staging 部署中创建可重复使用的**应用账号**。它不会创建 MySQL 身份，也绝不能
用于生产账号。

## 已配置的 staging 身份

MCS21 staging 数据库已于 2026-08-12 创建并核验以下身份：

| 用户名 | 应用角色 | 预期测试用途 |
|---|---|---|
| `admin` | `ADMIN` | 身份认证及后续管理员授权测试 |
| `test_user_1` | `USER` | 文件拥有者／上传者测试角色 |
| `test_user_2` | `USER` | 分享接收者及撤销访问测试角色 |

三个账号均已确认为 `ACTIVE`，并通过主机 Nginx 入口完成真实登录和已认证的
`/api/v1/auth/me` 请求。配置工具还会注销验证 Session，避免日常重复核验留下活动会话。

当前功能边界仍然不变：注册、登录、Session 和 `/auth/me` 已可用；文件、分享、审计查询、
恢复和管理员业务接口仍会按设计返回 `501 feature_not_implemented`。

## Secret 管理

Git 中不保存任何密码或 RSA 私钥。配置工具会在 staging VPS 的
`/srv/mcs21/test-accounts/` 下保存这些 Secret：

- 目录权限为 `0700`；
- `credentials.json` 和每个 `*-private-key.pem` 文件权限为 `0600`；
- 脚本不会输出密码、Access Token 或私钥。

测试人员应向获授权的项目负责人索取凭据，或从 VPS 受限目录读取。禁止把凭据粘贴到
GitHub、聊天、Issue、截图或部署日志。仓库会忽略 `test-accounts/` 目录及 PEM 文件作为第二道
防线，但文件权限和谨慎操作仍然是必要要求。

## 运行配置工具

部署主机必须满足：

- 应用可通过主机 Nginx 的 `http://127.0.0.1` 访问；
- 后端容器名为 `mcs21-staging-backend-1`，否则传入 `--container`；
- 操作者可执行 `docker exec`；
- `/srv/mcs21/test-accounts/` 位于所有 Git worktree 之外。

在 VPS 的仓库根目录运行：

```bash
sudo python3 scripts/provision_staging_test_accounts.py
```

部署参数不同时才显式覆盖：

```bash
sudo python3 scripts/provision_staging_test_accounts.py \
  --base-url http://127.0.0.1 \
  --container mcs21-staging-backend-1 \
  --output-dir /srv/mcs21/test-accounts
```

首次运行会通过正常注册 API 创建账号，因此密码哈希、RSA 密钥生成、账号持久化和注册审计
流程都会被真实执行。由于管理员 API 尚未实现，脚本随后会在后端容器内把账号设置为固定的
staging 角色。这种数据库外部角色设置只用于 staging 运维初始化，不能替代正式且带审计的
管理员工作流。

后续运行会复用已保存凭据、重新应用声明的角色，并再次核验登录、角色和注销。如果数据库中
已有账号但本地没有保存的凭据，注册会失败且脚本停止；脚本不会猜测或重置未知密码。私钥
缺失、应用不健康、角色不匹配或任何认证步骤失败时也会立即停止。

禁用、删除或轮换账号密码必须作为单独的 staging 变更协调执行。只要仍有加密测试数据依赖
这些私钥，就不能删除私钥。
