# 安全文件加密与共享平台

[English](README.md) | [简体中文](README.zh-CN.md)

安全文件加密与共享平台的毕业设计（FYP）架构。

## 项目目标

本系统允许用户上传文件、在服务器上以加密形式存储文件、与其他授权用户共享文件、撤销后续访问权限、验证文件完整性，并将安全敏感操作记录到可防篡改的审计日志中。

本项目重点关注：

- 服务端 AES 文件加密
- 基于 RSA 的文件密钥封装
- 受控共享与撤销
- 基于角色和文件级别的访问控制
- SHA-256 完整性验证
- 可防篡改的审计日志哈希链
- 针对例外访问场景的恢复治理

## 当前状态

后端身份认证纵向功能切片已完成，支持持久化账户、不透明访问令牌、轮换式一次性刷新令牌、可撤销会话、密码修改、基于数据库的限流、注册时使用的 RSA 密钥，以及在事务中追加的审计事件。九个 Auth 端点记录于 [API_DESIGN.zh-CN.md](docs/API_DESIGN.zh-CN.md)。

文件、共享、审计查询、恢复和管理业务 API 仍会显示在 OpenAPI 中，但会有意返回 `501 feature_not_implemented`。这些功能将在相应的授权、事务、审计、存储和拒绝访问测试完善后，按纵向功能切片逐一启用。

前端登录页已移除原型阶段的硬编码凭据绕过和演示令牌回退；后端响应缺少访问令牌时会直接
判定登录失败。完整的 refresh token 轮换、身份恢复和浏览器会话生命周期仍待实现，因此
当前前端仍不能作为生产级认证客户端。

项目按优先级排列的实施待办事项记录在 [TODO.zh-CN.md](TODO.zh-CN.md)。

## HTTP 方法策略

应用 API 只使用 `GET` 和 `POST`。`GET` 仅用于只读操作；新增、更新、删除、撤销及其他所有
会改变状态的动作均使用 `POST`。动作端点应在适当时采用显式路径，例如
`POST /api/v1/files/{file_id}/delete` 和
`POST /api/v1/auth/sessions/{session_id}/revoke`。应用路由和客户端不得使用 `PUT`、`PATCH`
或 `DELETE`，CORS 也只允许 `GET` 和 `POST` 方法。
浏览器或服务器所需的自动协议层处理（例如 CORS 预检）属于基础设施行为，不属于应用 API 操作。

## 推荐技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | FastAPI |
| 数据库 | MySQL 8.4 |
| 文件存储 | 用于 FYP 演示的本地加密文件存储 |
| 文件加密 | AES-256-GCM |
| 密钥封装 | 使用 SHA-256 的 RSA-OAEP |
| 密码哈希 | Argon2id（`pwdlib`） |

## 仓库结构

```text
fyp-secure-file-platform/
|-- backend/
|   |-- app/
|   |   |-- api/v1/routers/
|   |   |-- core/
|   |   |-- domain/
|   |   |-- models/
|   |   |-- repositories/
|   |   |-- schemas/
|   |   `-- services/
|   |-- migrations/
|   |-- tests/
|   `-- requirements.txt
|-- database/
|   `-- mysql/
|       |-- 01-provision.sql
|       |-- 02-schema.sql
|       `-- 03-verify.sql
|-- frontend/
|   |-- src/
|   `-- package.json
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- API_DESIGN.md
|   |-- DATABASE_SCHEMA.md
|   |-- DEPLOYMENT.md
|   |-- SECURITY_FLOWS.md
|   `-- PROJECT_SCOPE.md
|-- .env.example
|-- .gitignore
`-- docker-compose.yml
```

## 本地设置

Auth 端点已可用。其他业务端点仍以故障关闭方式返回 `501 feature_not_implemented`；健康检查和 OpenAPI 也可使用。

### 后端

运行下方迁移命令前，请确认目标数据库为空，或已经包含一条 `alembic_version` 记录。目前检查过的本地旧数据库不满足该条件；如果该数据库仍然存在，请跳过常规升级，并遵循下方的接管警告。

```bash
docker compose up -d --wait mysql
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Compose 会在全新本地 volume 上创建数据库及开发账户，因此上述命令只适用于本地开发。
Alembic 在本项目中保留为开发／CI 的 Schema 编写与一致性检查工具；生产和预发布服务器
不得运行 Alembic。对于由历史 `docs/init.sql` 创建的本地数据库，不得直接升级或标记版本；
请遵循 [DATABASE_SCHEMA.zh-CN.md](docs/DATABASE_SCHEMA.zh-CN.md) 中的说明。

### MySQL 部署

生产环境和预发布环境完全由 MySQL root／管理员按顺序执行三份经评审 SQL，不运行
Alembic，也不使用 Python 部署 runner 或 `fyp_migrator`：

```bash
# 数据库服务器仓库根目录；MySQL root 使用本机 socket 认证
sudo mysql < database/mysql/01-provision.sql
sudo mysql < database/mysql/02-schema.sql
sudo mysql < database/mysql/03-verify.sql
```

`01-provision.sql` 创建带 `REQUIRE SSL` 的 `fyp_user` 并返回 MySQL 随机密码；应把该密码
直接写入 secret store。`02-schema.sql` 只接受完全空的目标 Schema，创建最终表、种子、
兼容性 marker 及表级最小权限：11 张普通状态表拥有 CRUD，`audit_logs` 只有
`SELECT`／`INSERT`，`audit_chain_heads` 只有 `SELECT`／`UPDATE`，且应用无权访问
`alembic_version`。`03-verify.sql` 只读核验服务器、账户、精确权限和 Schema。
只有全部核验通过后，应用才通过标准 `DB_*` 以 `fyp_user` 启动。

三份 SQL 的账户 host 默认为 `localhost`。远程部署必须在仓库外制作三份受保护、经评审
副本，并一致替换其中每一个 `localhost` 账户 host 字面量。现有部署若遗留
`fyp_migrator`，须先确认其归属与用途，再显式撤权或删除。备份、串行化、失败恢复、
Compose 差异及未来非空数据库升级规则详见
[DEPLOYMENT.zh-CN.md](docs/DEPLOYMENT.zh-CN.md)。

OpenAPI：<http://localhost:8000/docs>

在 `backend/` 目录中运行后端质量检查：

```bash
ruff format --check app tests migrations
ruff check app tests migrations
pytest
alembic check
pip-audit -r requirements.txt
```

其中 `alembic check` 只用于开发／CI 漂移检查，不是生产部署步骤。

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端：<http://localhost:5173>

## 重要安全说明

本项目仍是 FYP 原型。内置的密码拒绝列表有意保持较小，并非持续维护的已泄露密码语料库。忘记密码恢复、电子邮件验证、多因素认证（MFA）以及外部身份提供商也需要可信的带外服务，目前尚未实现。生产环境部署还需要通过 KMS/HSM 加强密钥保管、强化运维、在外部锚定审计检查点，并接受专业安全审查。
