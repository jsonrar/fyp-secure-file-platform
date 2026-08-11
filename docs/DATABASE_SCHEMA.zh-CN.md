# 数据库 Schema 与迁移策略

[English](DATABASE_SCHEMA.md) | [简体中文](DATABASE_SCHEMA.zh-CN.md)

## Schema 权威与生产交付物

`backend/app/models/` 中的 SQLAlchemy metadata，以及 `backend/migrations/` 中按顺序排列的
Alembic revision，是开发与 CI 中编写和评审 Schema 演进的权威来源。生产环境不运行
Alembic；`database/mysql/02-schema.sql` 是由当前 head 派生并经过评审的空库生产
交付物。它不是可以独立修改的第二套设计，CI 必须持续证明其最终 Schema 与 ORM metadata
及 Alembic head 等价。

当前 revision 顺序如下：

1. `0001_initial_schema`：初始的用户、密钥、Session、文件、访问控制、完整性、审计及
   恢复 Schema。
2. `0002_auth_identity_sessions`：公开用户/Session UUID、access-session 演进、一次性
   refresh generation、持久化认证限流、密码修改时间，以及单例审计链头。

当前仓库不再保留 `docs/init.sql`。历史版本中的该文件不是当前应用 Schema 的权威来源，
Compose 也不会挂载任何生产表初始化脚本。后端启动时同样不得调用
`Base.metadata.create_all()`。

三份生产 SQL 的职责严格分离：

- `01-provision.sql` 创建固定数据库和唯一运行时账户 `fyp_user`，但不创建应用表；
- `02-schema.sql` 只在空数据库中创建当前完整 Schema、版本标记、单例初始行，并在表存在
  后授予 `fyp_user` 精确表级 DML；
- `03-verify.sql` 只读核验服务器、账户、所有权限层、完整 Schema、版本标记及单例状态。

生产没有 `fyp_migrator`。Schema 级、全局、DDL、role、proxy 或 `GRANT OPTION` 均不得授予
`fyp_user`。

## 开发与 CI 的迁移工作流

以下命令只在本地开发或 CI 的一次性 MySQL 8.4 数据库中从 `backend/` 运行：

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
或部署顺序。Revision 必须能安全地向前迁移现有数据，并同步更新及评审
`02-schema.sql`。Revision
`0002_auth_identity_sessions` 有意设计为只能向前迁移，因为它的公开 UUID、Session
generation、限流证据及密码哈希升级无法无损回退至 `0001`；回滚时应恢复备份，或重建
一次性开发数据库。

## 生产交付工作流

预发布及生产首次部署必须遵循 [DEPLOYMENT.zh-CN.md](DEPLOYMENT.zh-CN.md)：root/管理员从
仓库根目录以遇错停止的 batch 模式依次运行 `01-provision.sql`、仅限空库的
`02-schema.sql` 和只读的 `03-verify.sql`；最后应用以 `fyp_user` 启动。生产服务器不得
运行 `alembic upgrade/current/check/stamp`。

三份 SQL 都默认为 `localhost` 账户来源，Provision 账户要求 TLS。远程部署应在仓库外
制作三份经评审的受保护副本，把 `01` 的账户创建目标、`02` 的表级授权目标及 `03` 的
账户/授权期望一致替换为实际网络允许的最窄来源。

新账户的 MySQL 随机密码只能存入 secret store。发布编排器和操作员必须负责空库预检、
停止写入、串行执行、连接和 metadata-lock 超时、备份确认及失败恢复。若 `02-schema.sql`
发生部分 DDL 提交，不得通过 `IF NOT EXISTS`、覆盖或盲目重跑掩盖现场。

未来对非空生产数据库的变更必须使用独立、按版本命名、经 DBA 评审且只允许预期前置版本的
前向 SQL。每份升级 SQL 都需要配套备份/恢复、数据回填和发布后核验；不得以 Alembic 或
重跑完整 `02-schema.sql` 代替。

### 接管旧版或未受管理数据库

由历史 `docs/init.sql` 创建的数据库包含应用表，但没有可信的当前版本标记。**不要**对其
运行 `02-schema.sql`、`alembic upgrade head`，也不要在未经验证的情况下将它 stamp 为
当前版本：新基线
还会把 `files.storage_path` 重命名为 `storage_object_key`，并移除含义不明确的
`file_access_grants.permission_level` 列。

Migration `0002_auth_identity_sessions` 在开发/CI 中为已经到达 Alembic revision
`0001_initial` 的测试数据库提供安全回填；它不会接管未受管理的旧 Schema，也不会让
生产盲目 stamp 变得安全。它还要求 `audit_logs` 为空：非空的 revision-0001 审计链需要
经过评审的接管/checkpoint SQL，因为其历史哈希 payload 与时间戳精度无法无损转换。

- 如果旧数据库是一次性本地/CI 数据库且没有需要保留的数据，请重新创建，再选择开发
  Alembic 流程或完整三 SQL 生产演练流程。
- 如果生产数据库含有数据，请先创建并验证可恢复备份，再编写、评审一次性的版本化 DBA
  接管 SQL。绝不能仅仅为了让版本检查通过而重置、stamp 或覆盖数据库。

任何由该历史文件创建的 `fyp_secure_file_platform`，即使没有应用数据，只要它非空且没有
可信版本标记，就仍属于未受管理旧数据库。在明确将本地/CI 实例作为一次性数据库重建，或
通过经过评审的 DBA 接管流程处理之前，不得对其运行正常升级命令。完整 Schema SQL 和
Alembic 都不会自动安全接管它。

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

最低限度的开发/CI migration 测试从空数据库开始，通过 `alembic upgrade head` 应用
revision，检查当前 revision 及预期表，再运行 `alembic check` 检测 metadata drift，并
生成升级和降级的离线 SQL 供评审。

生产交付测试必须另建一个干净实例，按 `01-provision.sql -> 02-schema.sql ->
03-verify.sql` 执行，并比较该实例与 Alembic head 的表、列、索引、外键、CHECK、默认值及
种子行。它还必须证明 `02-schema.sql` 拒绝非空库、`03-verify.sql` 接受且只接受精确表级
权限，并拒绝任何 Host 的旧 `fyp_migrator`。未来添加旧数据库接管测试时，必须从明确的
旧版 fixture 开始，不能假装它已经处于 `0001_initial`。
