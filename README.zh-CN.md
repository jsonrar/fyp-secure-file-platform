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

后端 Auth 已就绪并不代表当前前端登录流程可用于生产环境：该页面仍包含原型阶段的凭据绕过／令牌回退逻辑。在进行端到端身份认证测试或部署之前，必须移除这些逻辑。

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
|   |-- scripts/
|   |-- tests/
|   `-- requirements.txt
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

对于空数据库，或已由当前 Alembic 迁移历史管理的数据库，执行 `alembic upgrade head` 是安全的。对于由旧版 `docs/init.sql` 创建的本地数据库，不得直接升级或标记版本；请遵循 [DATABASE_SCHEMA.zh-CN.md](docs/DATABASE_SCHEMA.zh-CN.md) 中的说明。

### MySQL 部署

生产环境和预发布环境使用 `backend/scripts/` 中带保护措施的脚本。它们会分别配置运行时账户和迁移账户、通过 MySQL advisory lock（咨询锁）串行执行迁移、拒绝未受管理的旧数据库架构、运行 Alembic 迁移至 head，并检查元数据漂移。

```bash
cd backend
python -m scripts.provision_mysql       # 仅首次部署；需要管理员变量
python -m scripts.deploy_mysql          # 空数据库
python -m scripts.deploy_mysql --confirm-backup  # 需要升级且已受管理的数据库
python -m scripts.verify_mysql
```

所需的密钥变量、账户权限、备份要求、发布顺序和回滚指南，请参阅 [DEPLOYMENT.zh-CN.md](docs/DEPLOYMENT.zh-CN.md)。部署脚本要求 MySQL 8.4 并启用严格 SQL 模式；脚本绝不会删除、重置未受管理的数据库，也不会为其强制标记迁移版本。

OpenAPI：<http://localhost:8000/docs>

在 `backend/` 目录中运行后端质量检查：

```bash
ruff format --check app tests migrations scripts
ruff check app tests migrations scripts
pytest
alembic check
pip-audit -r requirements.txt
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端：<http://localhost:5173>

## 重要安全说明

本项目仍是 FYP 原型。内置的密码拒绝列表有意保持较小，并非持续维护的已泄露密码语料库。忘记密码恢复、电子邮件验证、多因素认证（MFA）以及外部身份提供商也需要可信的带外服务，目前尚未实现。生产环境部署还需要通过 KMS/HSM 加强密钥保管、强化运维、在外部锚定审计检查点，并接受专业安全审查。
