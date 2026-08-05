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
| DELETE | `/auth/sessions/{session_id}` | Bearer 访问令牌 |

文件、共享、审计查询、恢复和管理端点仍是契约脚手架，并会有意返回 `501 feature_not_implemented`。`/health/live` 和 OpenAPI 仍然可用。只有在对应的授权、持久化、事务、审计、存储和拒绝访问测试全部完成后，才能解除这些路由的保护。

密码策略使用 Unicode NFC 进行规范化，要求密码长度为 15 至 128 个字符，拒绝由账户信息派生的值和常见值，并使用 Argon2id 进行哈希。有效的旧版 bcrypt 哈希会被透明升级；当配置的单工作进程容量已满时，内存密集型操作会快速失败。随附的常见密码列表只是一套小型本地安全基线，并非持续维护的已泄露密码语料库。忘记密码重置、电子邮件验证、多因素认证（MFA）和外部身份登录尚未实现；每项功能都需要可信的带外投递或身份通道。

## 前置要求

- Python 3.11 或更高版本
- 带 Compose 的 Docker（推荐用于 MySQL 8.4）

后端命令的规范执行目录是 `backend/`。配置始终从仓库根目录的 `.env` 加载，配置中的相对存储路径也会相对于仓库根目录解析，而不是相对于进程工作目录。

## 首次设置

在仓库根目录中，仅当 `.env` 尚不存在时才创建它：

执行 `alembic upgrade head` 前，请确认目标数据库为空，或已经包含一条 `alembic_version` 记录。目前检查过的本地旧数据库不满足该条件；请遵循[数据库接管策略](../docs/DATABASE_SCHEMA.zh-CN.md)，不要在该数据库上执行或强制标记常规迁移历史。

```powershell
Copy-Item .env.example .env
docker compose up -d --wait mysql
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
alembic upgrade head
```

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
ruff format --check app tests migrations scripts
ruff check app tests migrations scripts
pytest
alembic check
pip-audit -r requirements.txt
```

用于验证 ORM 行为的集成测试必须使用 MySQL 8.4，因为该架构使用了 MySQL 特有的无符号整数、枚举、二进制列、排序规则、JSON 和引用操作。不得使用 SQLite 替代这些测试的数据库。

## 数据库变更

架构演进由 Alembic 管理。应用程序绝不会调用 `create_all()`，Compose 也不再挂载会破坏数据的表初始化脚本。

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe the change"
alembic check
```

提交前请审查每一个自动生成的修订版本。

对于预发布环境或生产环境，请使用带保护措施的部署运行器，不要使用运行时数据库账户直接调用 Alembic：

```bash
python -m scripts.deploy_mysql
python -m scripts.verify_mysql
```

如果现有的受管理数据库落后于 head，还必须传入 `--confirm-backup`。账户配置方式和所有必需的环境变量记录于 [DEPLOYMENT.zh-CN.md](../docs/DEPLOYMENT.zh-CN.md)。

如果旧版本地数据库是由之前的 `docs/init.sql` 创建的，请在升级前阅读 `docs/DATABASE_SCHEMA.md` 中关于接管旧数据库的警告；不要对它执行 `upgrade head`，也不要盲目为其标记版本。Auth 迁移可以安全地接续 Alembic 基线，但不会将未受管理的旧架构转变成由 Alembic 管理的架构。

## 架构规则

精简的规则以及安全／事务边界记录于：

- [后端架构](../docs/ARCHITECTURE.zh-CN.md)
- [数据库架构策略](../docs/DATABASE_SCHEMA.zh-CN.md)
- [安全流程](../docs/SECURITY_FLOWS.zh-CN.md)
- [API 设计](../docs/API_DESIGN.zh-CN.md)

关键依赖规则是：路由器 -> 用例服务 -> 仓库／存储／加密策略。路由器不包含 SQL 或文件系统逻辑；仓库绝不提交事务；每个用例负责其自身的事务和存储补偿行为。
