# API 设计

[English](API_DESIGN.md) | 简体中文

## 当前状态

认证（Auth）是首个已实现的业务路由。其九个端点使用真实的持久化、事务、
服务端会话、限流、审计事件，以及 API/服务测试。

文件、共享、审计查询、恢复和管理员路由仍是契约占位实现。它们会出现在
OpenAPI 中，但在各路由具备真实的授权、持久化、事务所有权、审计行为、
适用时的存储处理及测试之前，均受 `501 feature_not_implemented` 保护。
这些路由不得返回演示令牌、硬编码用户或虚构的成功响应。

基础路径：

```text
/api/v1
```

应用层 HTTP 方法仅允许 `GET` 和 `POST`。`GET` 仅用于只读操作；新增、更新、删除、撤销及其他
所有会改变状态的命令均使用 `POST`，并在适当时采用显式动作路径。应用路由、客户端、示例和
OpenAPI 契约不得使用 `PUT`、`PATCH` 或 `DELETE`，CORS 也只允许 `GET` 和 `POST` 方法。
此限制不适用于 SQL 语句、数据库权限或外键动作。
浏览器或服务器所需的自动协议层行为（例如 CORS 预检处理）属于基础设施行为，不属于应用 API
操作。

未进行版本化的运维端点：

| 方法 | 端点 | 说明 |
|---|---|---|
| GET | /health/live | 进程存活检查；不检查依赖项 |

## 响应与错误契约

应用响应统一使用一个信封结构，而 `data` 内的公共 DTO 仍保持强类型：

```json
{
  "success": false,
  "status": "fail",
  "message": "Request validation failed",
  "data": {
    "error_code": "request_validation_failed",
    "details": []
  },
  "description": null,
  "code": 422
}
```

`error_code` 对客户端保持稳定；`message` 可安全展示给用户。内部异常文本、
请求体、凭据、密钥、数据库细节和文件系统路径绝不会返回。验证错误会指出
字段位置，但不会回显被拒绝的输入。

受保护路由通过 `Authorization: Bearer <token>` 接收不透明会话令牌。
认证失败响应包含 `WWW-Authenticate: Bearer`。每个 Auth 响应（包括验证错误
和领域错误）都包含 `Cache-Control: no-store, no-cache` 和
`Pragma: no-cache`；访问令牌、刷新令牌和注册时返回的私钥不得被缓存或记录
到日志中。

## Auth API

| 方法 | 端点 | 认证 | 成功状态码 | 说明 |
|---|---|---|---:|---|
| POST | `/auth/register` | 公开 | 201 | 创建一个 USER 账户，并仅返回一次其 RSA 私钥 |
| POST | `/auth/login` | 公开 | 200 | 验证 `username`/`password` 并签发一对访问/刷新凭据 |
| POST | `/auth/refresh` | JSON 请求体中的刷新令牌 | 200 | 消耗并轮换一次性刷新凭据 |
| GET | `/auth/me` | Bearer | 200 | 使用公共 UUID 返回当前账户 |
| POST | `/auth/logout` | Bearer | 200 | 撤销当前会话族 |
| POST | `/auth/logout-all` | Bearer | 200 | 撤销该账户的所有活跃会话族 |
| POST | `/auth/change-password` | Bearer | 200 | 验证当前密码、修改密码并撤销所有会话 |
| GET | `/auth/sessions` | Bearer | 200 | 列出最新的服务端会话，最多 100 个 |
| POST | `/auth/sessions/{session_id}/revoke` | Bearer | 200 | 通过公共 UUID 撤销一个属于该账户的会话 |

登录沿用 JSON 请求契约 `{ "username": "...", "password": "..." }`。
成功响应中的 `data` 对象为扁平结构，包含 `user`、`access_token`、
`refresh_token`、`token_type`、`access_expires_at`、`refresh_expires_at`
和 `session_id`。用户及会话的顺序数据库 ID 绝不会跨越 API 边界。

访问凭据和刷新凭据是彼此独立的不透明随机值。服务器只存储它们的 SHA-256
哈希。刷新凭据只能用于一次轮换；重放已消耗的凭据会撤销其完整会话族。
访问凭据的有效期较短，刷新凭据的有效期较长，且两者均受会话绝对到期时间
限制。

注册输入和新密码输入会进行 Unicode NFC 规范化。新密码必须包含 15 至 128
个字符，并在使用 Argon2id 哈希前通过本地常见密码及账户派生密码检查。
本地列表不是完整或持续维护的已泄露密码服务。

稳定的 Auth 错误包括 `invalid_credentials`、`authentication_required`、
`invalid_refresh_token`、`account_identifier_unavailable`、
`password_unchanged`、`weak_password`、`invalid_current_password`、
`session_not_found` 和 `auth_rate_limited`。429 响应提供 `Retry-After`；
认证错误绝不会区分未知、已禁用、已过期或已撤销的主体。

忘记密码重置、电子邮件验证、MFA 和外部身份提供商登录尚未实现。它们分别
需要可信的带外传递、注册或联合身份通道。账户元数据中存在
`email_verified`，并不表示验证流程已经存在。

## 尚未实现的业务 API

以下各节中的每个端点目前均返回 `501 feature_not_implemented`。

## 文件 API

| 方法 | 端点 | 说明 |
|---|---|---|
| POST | /files/upload | 上传并加密文件 |
| GET | /files | 列出当前用户可访问的文件 |
| GET | /files/{file_id} | 获取文件元数据 |
| POST | /files/{file_id}/download | 权限检查通过后下载并解密文件 |
| POST | /files/{file_id}/delete | 删除或禁用文件 |
| POST | /files/{file_id}/integrity-check | 验证加密文件哈希 |

## 共享 API

| 方法 | 端点 | 说明 |
|---|---|---|
| POST | /files/{file_id}/share | 与另一用户共享文件 |
| GET | /files/{file_id}/shared-users | 列出可访问该文件的用户 |
| POST | /files/{file_id}/revoke | 撤销某位用户的访问权限 |

## 审计 API

| 方法 | 端点 | 说明 |
|---|---|---|
| GET | /audit-logs | 列出审计日志 |
| GET | /audit-logs/file/{file_id} | 列出某文件的日志 |
| POST | /audit-logs/verify-chain | 验证审计哈希链 |

## 恢复 API

| 方法 | 端点 | 说明 |
|---|---|---|
| POST | /recovery/request | 创建恢复请求 |
| POST | /recovery/{request_id}/approve | 批准恢复请求 |
| POST | /recovery/{request_id}/execute | 执行恢复操作 |
| GET | /recovery/requests | 列出恢复请求 |

## 管理员 API

| 方法 | 端点 | 说明 |
|---|---|---|
| GET | /admin/users | 列出用户（仅限管理员） |
| GET | /admin/files | 列出文件记录（仅限管理员） |

## 契约规则

- 路由器声明请求和响应模型；ORM 对象和基础设施字典绝不会直接成为响应。
- 公共资源使用不透明标识符。顺序数据库 ID 仅供内部使用。
- 集合端点在实现前必须定义稳定排序，并提供分页或明确的结果数量硬上限。
  Auth 会话历史采用 100 行硬上限。
- 可能被重试的命令（上传完成、共享、撤销、执行恢复）需要幂等性或条件状态策略。
- 认证失败不会泄露账户、文件、会话或密钥是否存在。
