# 实施日志

[English](IMPLEMENTATION_LOG.md) | 简体中文

## 2026-08-11 — 数据库部署与集成门禁

**贡献者：** `Waldo0926`

### 已合并记录

- PR [#1](https://github.com/jsonrar/fyp-secure-file-platform/pull/1) 已合并到 `main`。
- 合并提交：`181e50a42022095ead2a40af2c77b8b71778913d`。
- 修复 MySQL 8.4 `0001 -> 0002` 外键索引顺序错误。
- 为 Alembic drift check 规范化等价的 MySQL 时间默认值。
- 令 ORM 时间默认值与已部署 Schema 保持一致。
- 删除硬编码管理员登录和假 Token 后备逻辑。

### 当前集成测试记录

- 分支：`agent/mysql84-integration-tests`。
- 增加必需的 GitHub Actions MySQL 8.4 发布门禁。
- 增加带命名保护、可销毁且不允许跳过测试的 MySQL fixture。
- 增加真实空库、已管理升级、重复部署、权限、约束和验证 TLS 测试。
- 增加可复现的 Docker 运行器，并在结束时销毁全部测试基础设施。
- 最终证据记录于
  [MySQL 8.4 集成测试报告](MYSQL_8_4_INTEGRATION_TEST_REPORT.zh-CN.md)。
