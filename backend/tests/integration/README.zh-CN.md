# 集成测试

[English](README.md) | [简体中文](README.zh-CN.md)

数据库、仓库和存储集成测试应放置于此，并且必须使用专用的、可随时销毁的 MySQL 8.4 数据库。绝不能让破坏性测试夹具指向常规开发数据库。请使用 `@pytest.mark.integration` 标记这些测试，并在实现第一个由数据库支持的纵向功能切片时添加它们。

## 必需的 MySQL 8.4 发布门禁

在仓库根目录运行完整隔离门禁：

```bash
./backend/tests/integration/run_mysql84_release_gate.sh
```

该运行器会创建临时 Docker 网络、全新的 MySQL 8.4、一次性 CA 与经过主机名验证的 TLS
证书，以及随机凭据。它真实验证：

- 空数据库直接迁移到 Alembic head；
- `0001_initial -> 0002_auth_identity_sessions` 升级；
- `alembic check` 不存在 metadata drift；
- 重复执行 provisioning、deployment 和 verification 不会丢失数据；
- 普通运行账户不能执行 DDL，而迁移账户可以；
- 唯一约束、外键与删除限制；
- 运行及迁移连接使用 TLS 1.3、账户具有 `REQUIRE SSL`，并拒绝显式禁用 TLS 的连接；
- 现有全部 Auth MySQL 集成测试，并且不允许跳过测试。

可销毁数据库和账户必须通过 `_test` 与 `mcs21_gate_` 命名保护。运行结束时会销毁测试
容器、网络、凭据、证书和数据库，不读取 `.env`，也不会连接常规开发或 staging 数据库。

GitHub 会通过 `.github/workflows/mysql84-release-gate.yml`，在相关 PR 和 `main` push 上运行
同一个命令。

最新运行证据记录于
[MySQL 8.4 集成测试报告](../../../docs/MYSQL_8_4_INTEGRATION_TEST_REPORT.zh-CN.md)。
