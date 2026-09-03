# 安全文件加密与共享平台

[English](README.md) | [简体中文](README.zh-CN.md)

安全文件加密与共享平台的毕业设计（FYP）架构。

## 预发布环境

当前版本运行在 **https://secureview.tech**。线上 API 可通过
[Swagger UI](https://secureview.tech/docs) 查看和演示，机器可读契约位于
[OpenAPI JSON](https://secureview.tech/openapi.json)。

对外书写与分享链接时请**一律带 `https://` 前缀**。`.tech` 不在浏览器 HSTS 预加载名单中，
直接输入裸域名的访客会先经过一次 `http://` 才被跳转，部分应用内置浏览器（含微信）会在这一跳
期间提示不安全。完成一次 HTTPS 访问后，`Strict-Transport-Security` 头会将协议固定一年。

HTTPS 不只关系到地址栏那把锁，而是产品能否运行的前提：浏览器只在安全上下文中暴露
`crypto.subtle`，而注册流程正是用它生成账户 RSA 密钥对并派生 Argon2id 密钥加密密钥。

## 项目目标

本系统允许用户上传文件、在服务器上以加密形式存储文件、与其他授权用户共享文件、撤销后续访问权限、验证文件完整性，并将安全敏感操作记录到可防篡改的审计日志中。

本项目重点关注：

- 客户端 AES-GCM（128/192/256 位密钥）与 ChaCha20-Poly1305 文件加密
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

浏览器 MVP 已端到端可运行：邮箱验证码注册与重置登录密码、客户端账户密钥登记、使用
passphrase 或私钥文件解锁、空闲自动上锁、上传前认证加密、下载后本地解密、文件名搜索、将
文件密钥重新包装给接收者的共享、撤销、逐文件访问历史、静默刷新会话、登出及注销账户。
每个文件可选择 AES-128/192/256-GCM 或 ChaCha20-Poly1305，默认仍为 AES-256-GCM；旧有硬编码
凭据和演示 token 后备均已移除。

剩余工作属于生产级加固，而非基础演示尚未闭环：强制 CI/MySQL 8.4 门禁、修改 passphrase 与
后继密钥 UI、完整管理/恢复专员页面、加密异地备份与恢复演练、定时对账、可观测性及正式安全
评审。优先级摘要见 [TODO.zh-CN.md](TODO.zh-CN.md)，带验收标准的可执行工作统一放在
[GitHub Issues](https://github.com/jsonrar/fyp-secure-file-platform/issues)。

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
| 文件加密 | AES-128/192/256-GCM 与 ChaCha20-Poly1305（默认 AES-256-GCM） |
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
|-- deployment/
|   `-- server/
|       |-- mcs21-deploy
|       |-- mcs21-auto-deploy
|       |-- mcs21-auto-deploy.service
|       `-- mcs21-auto-deploy.timer
|-- frontend/
|   |-- src/
|   `-- package.json
|-- changelog/
|   |-- CHANGELOG.md
|   |-- README.md
|   `-- work-packages/
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- API_DESIGN.md
|   |-- DATABASE_SCHEMA.md
|   |-- DEPLOYMENT.md
|   |-- AUTOMATIC_DEPLOYMENT.md
|   |-- SECURITY_FLOWS.md
|   `-- PROJECT_SCOPE.md
|-- .env.example
|-- .gitignore
`-- docker-compose.yml
```

## 更改日志

团队做过的所有变更及其原因，都记录在 [`changelog/CHANGELOG.md`](changelog/CHANGELOG.md)；
分工作包的记录存放在 [`changelog/work-packages/`](changelog/work-packages/)。添加条目前请先读
[`changelog/README.md`](changelog/README.md)，其中写明了哪类记录该写进哪一份。

## 团队工作流与唯一事实来源

- `changelog/CHANGELOG.md`：已经交付了什么，以及为什么重要。
- GitHub Issues：剩余可执行工作、负责人、讨论及验收标准。
- `TODO.zh-CN.md`：链接到 Issues 的优先级摘要，不再维护第二套独立 backlog。
- `README.zh-CN.md`：面向用户的当前能力、设置步骤与部署入口。

每个 Pull Request 都必须检查以上四处，更新受影响的记录；若不适用则说明 `N/A`。运行时改动不能
在 merge 时就算完成：`main` 部署后还必须记录线上 SHA，并验证健康检查和实际受影响页面。仓库的
Pull Request 模板已包含该清单。

## 本地设置

所有后端业务路由均已可用。存活检查、readiness 和 OpenAPI 也已启用；受保护路由要求
Bearer 身份认证，管理及恢复路由执行 RBAC。Readiness 会检查数据库连接及精确的
`0006_chacha20_poly1305` Schema revision。

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
空数据库的非幂等安装器：它创建 17 张表，对其中 14 张普通状态表授予 CRUD，
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

预发布 VPS 会在经过评审的 Pull Request 合并进 `main` 后自动部署对应 commit。服务器拉取
流程、队员操作命令、失败 SHA 隔离和凭据边界详见
[AUTOMATIC_DEPLOYMENT.zh-CN.md](docs/AUTOMATIC_DEPLOYMENT.zh-CN.md)。

OpenAPI：本地为 <http://localhost:8000/docs>，公网预发布为
<https://secureview.tech/docs>。

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

本项目仍是 FYP 原型。邮箱验证和忘记**登录密码**后的验证码重置已经实现，但 MFA 与外部身份
提供商尚未实现。加密 passphrase 与登录密码相互独立，且永不发送到服务器；遗忘 passphrase
时仍需用户另行保存的私钥文件，现有恢复不会重置已存储的 passphrase。内置密码拒绝列表有意
保持较小，并非持续维护的已泄露密码语料库。生产部署还需要加密异地备份与恢复演练、通过
KMS/HSM 或等效离线控制加强恢复密钥托管、在数据库外锚定审计 checkpoint，并接受独立专业
安全评审。
