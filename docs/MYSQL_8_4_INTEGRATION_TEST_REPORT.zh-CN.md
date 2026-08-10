# MySQL 8.4 集成测试报告

[English](MYSQL_8_4_INTEGRATION_TEST_REPORT.md) | 简体中文

## 结果

- **状态：** 通过
- **执行人：** `Waldo0926`
- **日期：** 2026-08-11
- **最终运行时间：** 04:04:59-04:05:45，Asia/Kuala_Lumpur
- **源码分支：** `agent/mysql84-integration-tests`，基于合并提交 `181e50a`
- **环境：** 项目 VPS 上的隔离 Docker 网络；`mysql:8.4` 与 Python 3.12.13
- **数据边界：** 未使用 staging 数据库、账号、凭据或应用数据

运行器生成一次性凭据、一次性 CA，以及仅对可销毁主机名 `mysql84-gate` 有效的服务器
证书。CA 私钥未挂载到任何测试容器。运行结束后，MySQL 容器、网络、数据库、账户、
凭据、证书和测试镜像均已删除。

## 最终证据

| 检查项 | 结果 |
|---|---|
| 应用、Migration、脚本及测试的 Ruff 检查 | 通过 |
| API 与单元测试 | 7.16 秒内 `108 passed, 14 deselected` |
| 真实 MySQL 8.4 集成测试 | 4.58 秒内 `14 passed, 108 deselected` |
| 必需集成门禁中跳过的测试 | `0` |
| 空数据库直接迁移到 Alembic head | 通过，版本为 `0002_auth_identity_sessions` |
| 真实 `0001_initial -> 0002_auth_identity_sessions` 升级 | 通过 |
| 已管理数据库升级前的备份确认拒绝 | 通过 |
| `alembic check` metadata drift | 无漂移 |
| 重复 provision/deploy/verify | 通过；哨兵数据与表集合保持不变 |
| 普通运行账户执行 DDL | 正确拒绝 |
| 迁移账户执行 DDL | 正确允许 |
| 唯一约束、外键与删除限制 | 通过 |
| 运行账户与迁移账户 TLS | TLS 1.3，证书及主机名验证通过 |
| 账户与不安全传输 | 账户为 `REQUIRE SSL`；显式非 TLS 连接被拒绝 |

## 修正日志

1. 第一次基础设施运行在测试前停止，因为 macOS 归档包含 AppleDouble `._*` metadata
   文件。仓库现已增加 `.dockerignore`，确保 Mac 生成的构建上下文在 Linux 中安全使用。
2. 第二次运行进入真实数据库，结果为 `118 passed, 4 failed`。其中三项是 CI TLS 环境变量
   影响了原本刻意构造开发配置的单元测试，因此现在将单元与集成阶段完全隔离。另一项证明
   MySQL 已拒绝非 TLS 登录，但返回 1045 而非 3159；在先证明同一凭据能以经过验证的 TLS
   1.3 成功连接后，断言现接受这两种安全拒绝形式。
3. 最终运行在隔离的单元与集成阶段通过全部 122 项已选择测试，集成测试无跳过。

## 复现方法

在具有 Docker 的主机上，从仓库根目录运行：

```bash
./backend/tests/integration/run_mysql84_release_gate.sh
```

GitHub 会通过 `.github/workflows/mysql84-release-gate.yml`，在相关 PR 和 `main` push 上运行
同一个命令。
