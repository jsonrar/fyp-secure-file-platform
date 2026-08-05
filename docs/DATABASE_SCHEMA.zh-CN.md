# 数据库 Schema 与迁移策略

[English](DATABASE_SCHEMA.md) | [简体中文](DATABASE_SCHEMA.zh-CN.md)

## 唯一事实来源

`backend/app/models/` 中的 SQLAlchemy metadata，以及 `backend/migrations/` 中按顺序排列的
Alembic revision，是 Schema 的唯一权威来源。

当前 revision 顺序如下：

1. `0001_initial_schema`：初始的用户、密钥、Session、文件、访问控制、完整性、审计及
   恢复 Schema。
2. `0002_auth_identity_sessions`：公开用户/Session UUID、access-session 演进、一次性
   refresh generation、持久化认证限流、密码修改时间，以及单例审计链头。

`docs/init.sql` 不是应用 Schema，也不会由 Compose 挂载。手动配置时，它可以创建一个
空的开发数据库，但绝不能创建/删除应用表。后端启动时同样不得调用
`Base.metadata.create_all()`。

## 迁移工作流

从 `backend/` 目录运行命令：

```bash
alembic upgrade head
alembic current
alembic check
```

有意修改 ORM Model 后：

```bash
alembic revision --autogenerate -m "describe the schema change"
```

务必评审自动生成的 revision。Autogenerate 无法理解数据迁移、应用不变量、安全的列回填
或部署顺序。Revision 必须能安全地向前迁移现有数据。Revision
`0002_auth_identity_sessions` 有意设计为只能向前迁移，因为它的公开 UUID、Session
generation、限流证据及密码哈希升级无法无损回退至 `0001`；回滚时应恢复备份，或重建
一次性开发数据库。

预发布及生产发布必须使用 [DEPLOYMENT.zh-CN.md](DEPLOYMENT.zh-CN.md) 中受防护的 MySQL
工作流。该工作流使用专用迁移身份、检查 Schema 所有权，并要求在升级已管理数据库前
明确确认备份。

### 接管旧版开发数据库

由旧版 `docs/init.sql` 创建的数据库包含应用表，但没有 `alembic_version` 行。**不要**对其
运行 `alembic upgrade head`，也不要在未经验证的情况下将它 stamp 为当前版本：新基线
还会把 `files.storage_path` 重命名为 `storage_object_key`，并移除含义不明确的
`file_access_grants.permission_level` 列。

Migration `0002_auth_identity_sessions` 为已经到达 Alembic revision
`0001_initial` 的数据库提供安全回填；它不会接管未受管理的旧 Schema，也不会让盲目
stamp 变得安全。它还要求 `audit_logs` 为空：非空的 revision-0001 审计链需要经过评审的
接管/checkpoint migration，因为其历史哈希 payload 与时间戳精度无法进行无损转换。

- 如果旧数据库是一次性的且没有需要保留的数据，请重新创建该数据库，再运行
  `alembic upgrade head`。
- 如果其中含有数据，请先备份，再编写并评审一次性的接管 migration，在 stamp 基线前
  完成上述转换。绝不能仅仅为了让 Alembic 通过而重置数据库。

上次检查工作区时，现有本地 `fyp_secure_file_platform` 数据库仍包含旧版的十张应用表、
没有 `alembic_version` 行，且没有应用数据。因此它仍属于旧数据库：在明确将其作为一次性
数据库重建，或通过经过评审的接管流程处理之前，不得对其运行正常升级命令。本仓库中的
任何 migration 命令都不会在无提示的情况下删除或接管它。

## 数据表分组

| 领域 | 数据表 | 用途 |
|---|---|---|
| 身份 | `users`, `user_sessions`, `session_refresh_tokens`, `user_keys` | 账户、不透明 access session、一次性 refresh generation、公钥历史 |
| 滥用控制 | `auth_login_throttles` | 在各 worker 间共享、以 HMAC 为 key 的登录、重新认证及注册 bucket |
| 文件 | `files`, `file_access_grants`, `file_key_wrappings` | 加密对象 metadata，以及逻辑和密码学访问控制 |
| 保障 | `integrity_checks`, `audit_logs`, `audit_chain_heads` | 验证历史、安全事件及串行化审计链追加状态 |
| 恢复 | `recovery_keys`, `recovery_requests` | 恢复公钥及经办-复核工作流 |

本地加密对象本身不存储于 MySQL。`files` 行存储不透明的存储对象 key；存储适配器在其
已配置的根目录内解析该 key。

## 必需不变量

以下是事务级不变量；即使 MySQL 无法直接、完整地表达它们，也必须通过集成测试验证：

1. 公开用户/Session UUID 必须唯一；数字主键和外键绝不能进入 API DTO。原始 access 与
   refresh 凭据绝不能进入数据库行。
2. 每个 Session 有一个当前 access 哈希及按单调递增编号的 refresh 记录。Refresh
   `(session_id, generation)` 和 token 哈希必须唯一。已消费 token 不得再次被接受；
   重放会撤销整个 Session family。
3. Access 过期时间不得晚于 Session 绝对过期时间。Refresh 过期时间受同一绝对过期时间
   限制；撤销 family 后，其所有凭据均不可再用。
4. 认证限流 key 是从 secret、scope 及规范化标识符/IP 派生的 HMAC-SHA-256 值。明文
   用户名和 IP 不得用作限流主键。
5. 注册以原子方式创建账户、公钥/指纹及审计事件；只有响应会收到 RSA 私钥。
6. 修改密码以原子方式替换 Argon2id 哈希、记录 `password_changed_at`、撤销所有活跃
   Session family，并追加审计事件。
7. 创建文件时，以原子方式创建其 metadata、所有者授权、所有者密钥包装、恢复密钥包装
   （启用时）及上传审计事件。
8. 下载同时要求：同一文件及行为者具有包含下载能力的有效授权，以及有效的用户密钥包装。
9. `USER` 密钥包装包含 `recipient_user_id` 和 `user_key_id`，但不含
   `recovery_key_id`。`RECOVERY` 包装只包含 `recovery_key_id`。
10. 撤销操作在同一事务中修改逻辑授权及所有适用的密钥包装。
11. 恢复状态转换必须符合条件且单调：
    `PENDING -> APPROVED|REJECTED|CANCELLED`，然后 `APPROVED -> EXECUTED`。
    请求者不能批准自己的请求。
12. 审计行只能追加。追加时锁定单例 `audit_chain_heads.id = 1`，因此并发事务无法创建
    两条具有同一前置项的记录；审计追加与其安全敏感用例一同提交或回滚。行为者/目标
    用户外键采用限制型约束，因为这些 ID 已进入哈希；被引用的账户采用基于状态的软删除，
    而非级联硬删除。
13. 普通查询排除已软删除文件，且不能再向这些文件授予新权限。

服务层拥有这些事务。Repository 可以查询、添加及执行 `flush`，但不得自行提交。

## 时间与标识符约定

- API 时间戳使用含时区的 UTC ISO-8601 值。
- MySQL `DATETIME` 值以 UTC 写入/读取；转换发生在 API 边界。
- 公开 URL 使用 UUID/不透明标识符，包括账户和 Session 资源。自增 ID 仅作为数据库
  内部 key。
- 存储对象 key、原始 Session 凭据、token 哈希、密钥材料、限流 HMAC 及文件系统根目录
  绝不能出现在日志或公开 API Schema 中。

## 集成测试数据库

Model 使用 MySQL 专属的 `UNSIGNED`、`ENUM`、`VARBINARY`、JSON、collation 及引用操作。
因此，Schema 与 Repository 集成测试针对 MySQL 8.4 运行。SQLite 不能作为行为等价的
替代品。

最低限度的 migration 测试从空数据库开始，按顺序通过 `alembic upgrade head` 应用
revision，检查当前 revision 及预期表，然后运行 `alembic check` 检测 metadata drift。
同时还会生成升级和降级的离线 SQL 供评审。未来添加旧数据库接管测试时，必须从明确的
旧版 fixture 开始，不能假装它已经处于 revision `0001_initial`。
