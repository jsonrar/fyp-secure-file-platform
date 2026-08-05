# MySQL 部署

[English](DEPLOYMENT.md) | [简体中文](DEPLOYMENT.zh-CN.md)

本文说明如何将数据库 Schema 部署至 MySQL 8.4。SQLAlchemy Model 和 Alembic revision
仍是 Schema 的唯一事实来源；部署脚本不会维护第二份 Schema dump，也绝不会运行
`create_all()`。

请在已安装生产环境 Python 依赖项的情况下，从 `backend/` 目录运行所有命令：

```bash
python -m pip install -r requirements.txt
```

## 必需配置

通过部署环境或已排除在版本控制外的根目录 `.env` 注入 secret。不要在命令行中写入密码。

应用/运行时身份使用现有设置：

- `DB_HOST`、`DB_PORT` 和 `DB_NAME`
- `DB_USER` 和 `DB_PASSWORD`
- `DB_SSL_CA`：可读取的 CA bundle，用于验证服务器证书及 `DB_HOST`

当服务器要求双向 TLS 时，还可同时设置 `DB_SSL_CERT` 和 `DB_SSL_KEY`。除开发/测试环境
外，必须使用经过验证的 TLS；服务器证书中必须包含每一个已配置的数据库/管理员主机名。
CA/client 文件应作为挂载的部署 secret 保存，不得存入 Git。

部署 runner 使用独立身份：

- `MIGRATION_DB_USER`
- `MIGRATION_DB_PASSWORD`

常规的非开发环境设置也必须提供：`APP_ENV` 必须标识目标环境，`APP_DEBUG=false`，
`SECRET_KEY` 必须是至少 32 个字符的非默认值，且必须明确列出 CORS origin。

数据库 provision 还需要以下临时管理员值：

- `MYSQL_ADMIN_USER` 和 `MYSQL_ADMIN_PASSWORD`
- 当管理员连接与 `DB_HOST`、`DB_PORT` 不同时，设置 `MYSQL_ADMIN_HOST` 和
  `MYSQL_ADMIN_PORT`
- `MYSQL_RUNTIME_USER_HOST`：应用 MySQL 账户的主机 pattern
- `MYSQL_MIGRATION_USER_HOST`：部署 runner 账户的主机 pattern

账户主机 pattern 是 MySQL 对连接来源主机的限制，并非数据库服务器地址。应选择部署网络
允许的最窄值。MySQL 接受 `%`，但只有在网络与防火墙已另外限制的私有网络中才应使用它。

## 账户 Provision

对于新的自托管 MySQL 实例，使用能够创建数据库、用户及 grant 的管理员运行一次以下命令。
Grant 校验还要求该管理员能够检查其他账户的 grant（通常需要 MySQL 系统 Schema 的
`SELECT` 权限）：

```bash
python -m scripts.provision_mysql
```

只要两个身份继续专用于该数据库，此命令可安全地重复运行。它会使用 `utf8mb4` 和
`utf8mb4_unicode_ci` 创建 `DB_NAME`、创建缺失的账户，并重新应用限定于该 Schema 的
grant。它不会创建应用表。

现有账户的密码会被有意保留、不作修改。若已协调应用发布并要执行有意的凭据轮换，请使用：

```bash
python -m scripts.provision_mysql --rotate-passwords
```

在开发/测试环境之外，两个账户均以 `REQUIRE SSL` 创建。运行时账户仅获得 `SELECT`、
`INSERT`、`UPDATE` 和 `DELETE`。迁移账户还会获得该数据库上的 `CREATE`、`DROP`、
`ALTER`、`INDEX`、`REFERENCES` 和 `CREATE TEMPORARY TABLES`。它不会获得任何全局
权限。托管数据库服务也可以通过其控制平面 provision 这些身份；最终的 grant 和环境变量
必须等效。

当现有身份具有全局、role、proxy、grant-option、其他数据库、表级或多余的 Schema 权限
时，provision 会失败关闭。请使用新的专用身份，或以管理员身份评审并移除多余 grant；
脚本绝不会自动撤销无关账户的访问权限。

运行时身份是在数据库/DDL 边界而非逐表边界上受限：其 DML grant 也涵盖审计表和 migration
metadata 表。如果威胁模型包含运行时数据库凭据被盗，则应引入经过评审的表级专用身份
或存储过程，并在外部锚定审计 checkpoint，之后才能将审计链视为具备独立防篡改能力。

Provision 完成后，请立即从部署环境中移除 `MYSQL_ADMIN_PASSWORD`。Migration 和验证
命令均不需要管理员凭据。

## 发布顺序

1. 确认目标为 MySQL 8.4、已启用 strict SQL mode，并且 Schema 升级过程中应用不会写入。
2. 对于已经由 Alembic 管理、但落后于仓库 head 的数据库，创建并验证可恢复的备份。
   MySQL DDL 并非完全事务化。
3. 启动新版应用前运行 migration。
4. 使用运行时身份验证 Schema。

对于新的空数据库：

```bash
python -m scripts.deploy_mysql
python -m scripts.verify_mysql
```

对于需要升级、已由 Alembic 管理的现有数据库：

```bash
python -m scripts.deploy_mysql --confirm-backup
python -m scripts.verify_mysql
```

`--confirm-backup` 记录的是操作员声明，并不会创建备份。备份应存储在本仓库之外、经过
加密、限制访问，并定期测试恢复。数据库 dump 包含账户哈希、安全审计证据、加密文件
metadata 和已包装 key。

Migration runner 会等待连接、验证服务器与数据库编码、设置并验证 UTC Session 时区，
以及获取数据库专属的 MySQL advisory lock。它只允许完全为空的数据库，或与某个已知
Alembic revision 完全匹配的 Schema。执行 `alembic upgrade head` 后，它会检查 revision、
预期表集合、单例审计链头和 Alembic metadata drift。数据库已在 head 时，第二次运行具有
幂等性，无需确认备份。

当编排器需要不同的等待时间时，两个命令都接受有界等待选项：

```bash
python -m scripts.deploy_mysql --wait-timeout 120 --lock-timeout 120
python -m scripts.verify_mysql --wait-timeout 60 --lock-timeout 60
```

## 旧数据库与部署失败

没有 `alembic_version` 的非空数据库不受管理。Runner 会停止，而不会升级、stamp、删除
或重置数据库。请遵循[旧数据库接管策略](DATABASE_SCHEMA.zh-CN.md)；绝不能仅为了绕过
防护而使用 `alembic stamp`。

Revision `0002_auth_identity_sessions` 也会拒绝审计链已经包含数据行的 revision-`0001`
数据库。该历史需要经过评审的接管/checkpoint migration。

如果 migration 失败，请保持应用停止，并保留数据库供诊断。由于当前 `0002` 数据转换
有意设计为只能向前迁移，而且 MySQL DDL 可能增量提交，因此回滚意味着恢复已验证的
部署前备份。不要运行 `alembic downgrade`、手动编辑 `alembic_version`，也不要把带密码
轮换的 provision 重新运行作为恢复手段。

## 容器说明

根目录 `docker-compose.yml` 是本地 MySQL 服务，不是生产部署栈。不要将 migration 挂载到
`/docker-entrypoint-initdb.d`：官方镜像的初始化只会对全新数据卷运行，因此现有部署会
在没有提示的情况下错过后续 Schema revision。应改为把受防护的 migration 命令作为明确
的发布 Job 运行。
