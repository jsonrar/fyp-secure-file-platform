# 安全文件加密与共享平台

[English](README.md) | [简体中文](README.zh-CN.md)

安全文件加密与共享平台的毕业设计（FYP）架构。

## 项目目标

本系统允许用户上传文件、在服务器上以加密形式存储文件、与其他授权用户共享文件、撤销后续访问权限、验证文件完整性，并将安全敏感操作记录到可防篡改的审计日志中。

本项目重点关注：

- 客户端 AES-256-GCM 文件加密
- 基于 RSA 的文件密钥封装
- 受控共享与撤销
- 基于角色和文件级别的访问控制
- SHA-256 完整性验证
- 可防篡改的审计日志哈希链
- 针对例外访问场景的恢复治理

## 当前状态

后端身份认证、客户端包装密钥托管、加密文件、共享、审计查询、由离线流程治理的恢复及管理／RBAC
API 均已实现。服务器只持久化公钥、加密私钥包、密文和已包装的文件密钥；用户的加密
passphrase、KEK、AMK、明文私钥、文件 DEK 和文件明文都不得出现在 API 请求或数据库记录中。
注册及文件／密钥流程详见 [SECURITY_FLOWS.zh-CN.md](docs/SECURITY_FLOWS.zh-CN.md)。

前端登录页已调用真实 Auth 端点，后端响应缺少访问令牌时会直接判定登录失败；原型阶段的
硬编码凭据绕过和演示令牌回退已经移除。不过，浏览器端的账户密钥登记、私钥解锁、文件
加解密及 DEK 重包装仍未实现，refresh、过期和已撤销会话处理也仍需生产级加固。因此，
后端完成并不代表当前浏览器 UI 已经具备完整的客户端密码学流程。

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

所有后端业务路由均已可用。存活检查、readiness 和 OpenAPI 也已启用；受保护路由要求
Bearer 身份认证，管理及恢复路由执行 RBAC。Readiness 会检查数据库连接及精确的
`0003_client_key_custody` Schema revision。

`MAX_REQUEST_BODY_BYTES` 限制普通 JSON／form 请求体（默认 1 MiB，配置上限 8 MiB）。加密
multipart 上传另受 `MAX_UPLOAD_SIZE_BYTES + MAX_UPLOAD_REQUEST_OVERHEAD_BYTES` 独立上限
约束，因此提高普通请求体上限不会改变允许上传的密文大小。

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

部署时应把唯一一次生成的 `fyp_user` 密码直接写入 secret store。`02-schema.sql` 是只接受
空数据库的非幂等安装器：它创建 15 张应用表，对其中 13 张普通状态表授予 CRUD，
对 `audit_logs` 仅授予 `SELECT`／`INSERT`，并把 `audit_chain_heads` 的更新权限限制在
`last_log_id`、`current_hash` 和 `updated_at` 三列，使运行时账户无法修改
`schema_revision`；应用也无权访问 `alembic_version`。`03-verify.sql` 只读核验精确 Schema
和权限，并必须确认已停用的 `fyp_migrator` 身份不存在。只有全部结果通过评审后，应用才
通过标准 `DB_*` 配置以 `fyp_user` 启动。

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

本项目仍是 FYP 原型。内置的密码拒绝列表有意保持较小，并非持续维护的已泄露密码语料库。
登录密码与仅由客户端处理的加密 passphrase 相互独立；用户通常只需记住加密 passphrase，
因为服务端保存的是可重新获取的加密私钥包。但若遗忘该 passphrase，且没有独立安全保存的
可用密钥副本，服务器目前无法重置或恢复它。现有恢复流程只治理单个文件 DEK 向已登记活跃
公钥的重新包装，不会恢复 passphrase、AMK 或解密私钥包。

忘记登录密码恢复、电子邮件验证、多因素认证（MFA）以及外部身份提供商也需要可信的带外
服务，目前尚未实现。生产部署还需要通过 KMS／HSM 加强密钥保管、强化运维、在外部锚定
审计检查点，并接受专业安全审查。
