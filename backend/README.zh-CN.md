# 后端

[English](README.md) | [简体中文](README.zh-CN.md)

安全文件加密与共享平台的 FastAPI 模块化单体后端。

## 当前状态

Auth 纵向功能切片已完成，不再受草案路由依赖项保护。它负责真实的 MySQL 事务、不透明访问凭据和轮换式刷新凭据、会话撤销、登录／注册限流、用户注册时使用的 RSA 密钥，以及通过哈希链串联的审计事件。以下九个端点已在 `/api/v1` 下启用：

| 方法 | 端点 | 身份认证 |
|---|---|---|
| POST | `/auth/register` | 公开 |
| POST | `/auth/login` | 公开 |
| POST | `/auth/refresh` | 刷新凭据 |
| GET | `/auth/me` | Bearer 访问令牌 |
| POST | `/auth/logout` | Bearer 访问令牌 |
| POST | `/auth/logout-all` | Bearer 访问令牌 |
| POST | `/auth/change-password` | Bearer 访问令牌 |
| GET | `/auth/sessions` | Bearer 访问令牌 |
| POST | `/auth/sessions/{session_id}/revoke` | Bearer 访问令牌 |

文件、共享、审计查询、恢复和管理端点仍是契约脚手架，并会有意返回 `501 feature_not_implemented`。`/health/live` 和 OpenAPI 仍然可用。只有在对应的授权、持久化、事务、审计、存储和拒绝访问测试全部完成后，才能解除这些路由的保护。

应用层 HTTP 端点仅使用 `GET` 和 `POST`：读取操作使用 `GET`，新增、更新、删除、撤销及其他
会改变状态的动作使用 `POST`。不得新增 `PUT`、`PATCH` 或 `DELETE` 路由；CORS 方法配置也
仅允许 `GET` 和 `POST`。

密码策略使用 Unicode NFC 进行规范化，要求密码长度为 15 至 128 个字符，拒绝由账户信息派生的值和常见值，并使用 Argon2id 进行哈希。有效的旧版 bcrypt 哈希会被透明升级；当配置的单工作进程容量已满时，内存密集型操作会快速失败。随附的常见密码列表只是一套小型本地安全基线，并非持续维护的已泄露密码语料库。忘记密码重置、电子邮件验证、多因素认证（MFA）和外部身份登录尚未实现；每项功能都需要可信的带外投递或身份通道。

## 前置要求

- Python 3.11 或更高版本
- 带 Compose 的 Docker（推荐用于 MySQL 8.4）

后端命令的规范执行目录是 `backend/`。配置始终从仓库根目录的 `.env` 加载，配置中的相对存储路径也会相对于仓库根目录解析，而不是相对于进程工作目录。

## 首次设置

在仓库根目录中，仅当 `.env` 尚不存在时才创建它：

以下 Alembic 步骤仅限本地开发。执行 `alembic upgrade head` 前，请确认目标数据库为空，
或已经包含一条 `alembic_version` 记录。目前检查过的本地旧数据库不满足该条件；请遵循
[数据库接管策略](../docs/DATABASE_SCHEMA.zh-CN.md)，不要在该数据库上执行或强制标记常规
迁移历史。

```powershell
Copy-Item .env.example .env
docker compose up -d --wait mysql
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
alembic upgrade head
```

Compose 只提供本地开发便捷环境：它会在全新 volume 上按 `DB_NAME`、`DB_USER` 和
`DB_PASSWORD` 创建数据库及开发账户，但不会执行生产用的账户 Provision 或权限核验 SQL。
生产／预发布环境必须遵循下方由 root／管理员执行的 SQL-only 流程。

macOS/Linux 激活命令：

```bash
source .venv/bin/activate
```

不要提交 `.env`、私钥、恢复密钥、运行时文件或加密测试数据。

## 运行

开发环境：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

OpenAPI：<http://localhost:8000/docs>

存活检查：<http://localhost:8000/health/live>

`--reload` 仅用于本地开发。部署时必须注入非默认密钥、设置 `APP_DEBUG=false`、明确配置 CORS 来源，并使用受监管的进程或容器。

## 质量检查

在 `backend/` 目录中运行：

```bash
ruff format --check app tests migrations
ruff check app tests migrations
pytest
alembic check
pip-audit -r requirements.txt
```

用于验证 ORM 行为的集成测试必须使用 MySQL 8.4，因为该架构使用了 MySQL 特有的无符号整数、枚举、二进制列、排序规则、JSON 和引用操作。不得使用 SQLite 替代这些测试的数据库。

## 数据库变更

Alembic revision 和 ORM metadata 用于本地开发／CI 中编写、评审和测试 Schema 变更。
应用程序绝不会调用 `create_all()`，Compose 也不再挂载会破坏数据的表初始化脚本。

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe the change"
alembic check
```

提交前必须审查每一个自动生成的 revision，并在 CI 中验证 Alembic head 与生产
`02-schema.sql` 的最终 Schema 一致。上述 Alembic 命令不是生产部署步骤。

预发布和生产环境不运行 Alembic，也不创建 `fyp_migrator`。数据库 root／管理员从仓库
根目录以遇错停止的 batch 模式依次执行：

```bash
# 数据库服务器仓库根目录；MySQL root 使用本机 socket 认证
sudo mysql < database/mysql/01-provision.sql
sudo mysql < database/mysql/02-schema.sql
sudo mysql < database/mysql/03-verify.sql
```

`01-provision.sql` 只创建固定数据库和带 `REQUIRE SSL` 的 `fyp_user`，并为新账户返回一个
随机密码；密码必须直接写入 secret store。`02-schema.sql` 只允许用于完全空的目标
Schema，它创建最终表、唯一应用种子和 `alembic_version` 兼容性 marker，并授予 11 张
普通状态表 CRUD、`audit_logs` 的 `SELECT`／`INSERT`、`audit_chain_heads` 的
`SELECT`／`UPDATE`；应用无权访问 `alembic_version`。
`03-verify.sql` 是只读核验。核验通过后，应用才通过标准 `DB_*` 以 `fyp_user` 启动；
root 凭据绝不能进入应用 `.env`。

三份 SQL 都以 `localhost` 为账户 host 默认值；远程部署应在仓库外制作三份受保护、经
评审的副本，并一致替换其中每一个 `localhost` 账户 host 字面量。若执行 02 时任何语句
失败，不得在部分 Schema 上重跑；应查明原因后重建一次性空库或恢复已验证备份。已有
非空生产库的后续升级必须使用新的、版本化且经 DBA 评审的 root SQL，不能重跑 02，
也不能在服务器上改用 Alembic。现有环境若遗留 `fyp_migrator`，须确认归属后显式撤权或
删除。停止写入、发布串行化、备份／恢复演练、DDL 超时和失败处置均由发布编排器与操作员
负责。完整要求见
[DEPLOYMENT.zh-CN.md](../docs/DEPLOYMENT.zh-CN.md)。

如果旧版本地数据库是由历史 `docs/init.sql` 创建的，请阅读
[数据库接管策略](../docs/DATABASE_SCHEMA.zh-CN.md)；不要对它执行 `upgrade head`，也不要
盲目标记版本。该警告仅说明本地开发接管；生产非空库必须走单独的 DBA SQL 升级方案。

## 架构规则

精简的规则以及安全／事务边界记录于：

- [后端架构](../docs/ARCHITECTURE.zh-CN.md)
- [数据库架构策略](../docs/DATABASE_SCHEMA.zh-CN.md)
- [安全流程](../docs/SECURITY_FLOWS.zh-CN.md)
- [API 设计](../docs/API_DESIGN.zh-CN.md)

关键依赖规则是：路由器 -> 用例服务 -> 仓库／存储／加密策略。路由器不包含 SQL 或文件系统逻辑；仓库绝不提交事务；每个用例负责其自身的事务和存储补偿行为。
