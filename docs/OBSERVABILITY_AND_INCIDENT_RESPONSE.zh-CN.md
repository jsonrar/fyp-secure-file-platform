# 可观测性、外部审计检查点与事故响应

[English](OBSERVABILITY_AND_INCIDENT_RESPONSE.md) | [简体中文](OBSERVABILITY_AND_INCIDENT_RESPONSE.zh-CN.md)

本文是 issue #59 的运维契约。原则是：遥测只记录**必要元数据**，让运维知道认证、存储、Schema、恢复或部署事件发生了什么，但日志与告警绝不能成为受保护数据的第二份副本。

## 1. 结构化脱敏日志

`backend/app/core/observability.py` 为 `app.*` logger 安装单行 JSON formatter。安全事件只允许固定字段：`event`、`category`、`outcome`、路由模板、状态码、耗时、request id、经过信任边界处理后的客户端 IP，以及少量固定运维字段。未知 extra 字段直接丢弃；最终 formatter 还会对旧式自由文本中的 Bearer credential、secret/password/passphrase/token 赋值、PEM 私钥块做兜底脱敏。

HTTP middleware 只记录 **FastAPI 路由模板**，不记录原始 URL。例如真实请求
`/api/v1/recovery/real-user-value/approve` 只会记录为
`/api/v1/recovery/{request_id}/approve`。可观测层从不读取 request/response body。

当前事件包括：

| 类别 | 事件 | 触发条件 |
|---|---|---|
| `auth` | `auth_rate_limited` | 认证路由返回 429 |
| `storage` | `storage_unavailable` | 存储服务返回受控不可用错误 |
| `storage` | `integrity_verification_rejected` | 密文被修改/缺失，下载被拒绝 |
| `database` | `database_unavailable` | readiness 无法完成数据库探测 |
| `schema` | `schema_mismatch` | 线上 Schema revision 与 release 不一致 |
| `recovery` | `recovery_operation` | recovery 路由成功或被拒绝 |
| `application` | `unhandled_application_error` | 未预期异常进入全局 handler |
| deployment | 既有 `mcs21-deploy` audit 记录 | deploy/rollback 结果、调用者、commit/目标和回滚点 |

`/var/log/mcs21-deploy/audit.log` 与 journald 中既有的 deploy audit 已是固定 key/value 记录，并且不包含环境变量内容、数据库密码、应用 secret、请求体、文件名或私钥。它继续作为部署事实来源；生产脚本禁止开启 `set -x`。

### 日志和告警中绝不能出现

- `Authorization` / refresh token、cookie、session hash、验证码或重置码；
- 密码、加密 passphrase、API key、数据库凭据、HMAC key；
- PEM/私钥材料、恢复私钥；
- 明文文件内容、明文文件名、用户提供的 MIME；
- 完整邮件正文或收件人地址；
- 任意 request/response body 或 exception locals。

`EMAIL_PROVIDER=console` 仍仅限开发环境，但现在只记录“邮件被抑制”，不会再输出收件人、主题、验证码、重置内容或正文。单元测试会注入明显的 secret canary，只要它进入格式化日志、monitor state 或 checkpoint artifact 就失败。

## 2. Metrics 与可执行告警

Backend 提供 `GET /internal/metrics` 的 Prometheus 文本。**nginx 不代理这个路径**，staging backend 只绑定 `127.0.0.1`；运维 monitor 直接从 loopback 读取。不要给它新增公网 nginx location。

Metrics 只有固定类别计数和 FastAPI 路由模板：

- `secureview_http_requests_total{method,route,status_class}`；
- `secureview_security_events_total{category,event,outcome}`；
- request duration sum/count。

`backend/scripts/ops_monitor.py` 每 5 分钟读取 `/health/ready` 和 `/internal/metrics`，状态文件 `/var/lib/fyp-secure-file-platform/ops-monitor/state.json` 只保存数字计数。它使用**增量**判断，旧故障不会一直重复告警；backend 重启导致计数器归零时会自动建立新基线。

| 每 5 分钟条件 | 阈值 | 处理/负责人 |
|---|---:|---|
| readiness 非 `ready` / metrics 不可达 | 1 | 立即告警；部署/测试负责人 |
| auth 被 rate limit | 20 | 查滥用、代理/IP、fail2ban |
| storage unavailable | 1 | 查磁盘/文件系统/服务 |
| ciphertext integrity rejection | 1 | 作为潜在损坏/篡改事件调查 |
| schema mismatch | 1 | 停止继续部署，核对 release/migration |
| database unavailable | 1 | 查 MySQL/TLS/磁盘/网络 |
| unexpected application exception | 1 | 用脱敏事件定位，禁止 dump 请求体 |
| recovery operation rejected | 5 | 检查 recovery 流程/角色滥用；安全负责人 |

`mcs21-ops-monitor.service` 命中阈值或 health 失败就非零退出，由
`OnFailure=mcs21-alert@%n.service` 复用 #57 已验证的邮件告警。真实收件人只存在
`/etc/fyp-secure-file-platform/alert.env`，不写入仓库。

## 3. Trusted proxy 与客户端 IP

应用**不会自己解析** `X-Forwarded-For` / `X-Real-IP`。`RequestContext` 与 observability middleware 都只使用 `request.client`。

线上唯一 HTTP 路径是：

```text
Internet client -> nginx :443 -> Uvicorn 127.0.0.1:8000
```

Uvicorn 必须使用：

```text
--proxy-headers --forwarded-allow-ips=127.0.0.1
```

这样只有 TCP peer 为本机 nginx 时才接受 forwarded headers。远端客户端无法直接访问 loopback backend，也无法让 Uvicorn 信任伪造的来源 IP。`mcs21-deploy` 的 preflight 已使用同一限制。

关闭 #59 前在真实主机记录：

```bash
systemctl cat fyp-backend | grep -F -- '--forwarded-allow-ips=127.0.0.1'
ss -ltnp | grep '127.0.0.1:8000'
```

任一项不满足，就先修 service，再依赖 IP throttling、fail2ban 或审计 IP。

## 4. MySQL 外部 HMAC 审计检查点

数据库内 audit chain 如果连 chain head 一起被整体重写，就缺少独立信任锚。
`backend/scripts/audit_checkpoint.py` 只签名一个极小快照：

```json
{
  "format": 1,
  "created_at_utc": "...",
  "last_log_id": 123,
  "current_hash": "<sha256>",
  "schema_revision": "0006_chacha20_poly1305"
}
```

记录包含 `hmac_sha256 = HMAC-SHA256(canonical payload)`。它不复制 audit description、metadata、身份、文件名、文件内容、token 或 key material。HMAC key 只能通过 `AUDIT_CHECKPOINT_HMAC_KEY` 提供。

生产 timer 每小时发布。本机 0600 副本写到
`/var/lib/fyp-secure-file-platform/audit-checkpoints`；`AUDIT_CHECKPOINT_DEST` **必须**是外部目的地（`s3://...` 或 `user@host:/...`）。staging 应使用现有带保留/锁定策略的 S3-compatible 异地存储中的独立 prefix。目的端账号尽量采用 put-only，HMAC key 不得进入数据库或 Git。

示例 `/etc/fyp-secure-file-platform/audit-checkpoint.env`（0600 root）：

```bash
AUDIT_CHECKPOINT_HMAC_KEY=<随机 >=32-byte secret>
AUDIT_CHECKPOINT_DEST=s3://<locked-bucket>/secureview-audit-checkpoints
AUDIT_CHECKPOINT_S3_ENDPOINT_URL=<如使用 S3-compatible provider>
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 只存在 secret store。
```

真实 key 不要粘贴到 issue、聊天或截图。

### 独立验证

把 checkpoint 下载到**另一台机器**，只在该机器环境中提供 HMAC key：

```bash
cd backend
AUDIT_CHECKPOINT_HMAC_KEY='...' .venv/bin/python scripts/audit_checkpoint.py \
  --verify /path/to/downloaded/checkpoints
```

任一 HMAC 错误、时间倒退或 `last_log_id` 倒退都会失败。即使之后应用数据库被改写，一个已验证的旧外部 checkpoint 仍然是可信历史锚。外部对象必须使用 object-lock/append-only/保留策略；否则攻击者删除全部旧 checkpoint 仍可抹掉历史。

## 5. Staging 安装

PR merge 并部署精确 merge SHA 后：

```bash
R=/opt/mcs21/current
cat "$R/.mcs21-release"

sudo install -d -o fypapp -g fypapp -m 0750 \
  /var/lib/fyp-secure-file-platform/ops-monitor \
  /var/lib/fyp-secure-file-platform/audit-checkpoints

sudo install -o root -g root -m 0644 \
  "$R/deployment/server/mcs21-ops-monitor.service" \
  "$R/deployment/server/mcs21-ops-monitor.timer" \
  "$R/deployment/server/mcs21-audit-checkpoint.service" \
  "$R/deployment/server/mcs21-audit-checkpoint.timer" \
  /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemd-analyze verify \
  /etc/systemd/system/mcs21-ops-monitor.service \
  /etc/systemd/system/mcs21-ops-monitor.timer \
  /etc/systemd/system/mcs21-audit-checkpoint.service \
  /etc/systemd/system/mcs21-audit-checkpoint.timer

sudo systemctl start mcs21-ops-monitor.service
sudo journalctl -u mcs21-ops-monitor.service -n 20 --no-pager
sudo systemctl start mcs21-audit-checkpoint.service
sudo journalctl -u mcs21-audit-checkpoint.service -n 20 --no-pager

sudo systemctl enable --now mcs21-ops-monitor.timer mcs21-audit-checkpoint.timer
systemctl list-timers mcs21-ops-monitor.timer mcs21-audit-checkpoint.timer --no-pager
```

然后至少下载两个外部 checkpoint 到另一台机器做独立 HMAC 验证。只有本机 checkpoint 不能关闭 #59。

## 6. 事故处理

### A. 服务宕机 / readiness 失败

1. `systemctl status fyp-backend nginx mcs21-mysql --no-pager`，并检查 loopback health。
2. 只看有界 journal（例如 `-n 100`）；禁止在线上打开 request-body/debug dump。
3. DB readiness 失败先查 MySQL health/TLS/disk，再决定重启。
4. release 导致故障时使用 `sudo mcs21-deploy rollback`，不要手工移动 symlink。
5. 保留 monitor/deploy 日志，记录时间、release SHA 和处置动作。

### B. 存储损坏 / integrity rejection

1. 不覆盖、不删除疑似密文；file UUID/object key 只写 root-only 事故记录，不把明文文件名贴到共享日志。
2. 执行现有 integrity/tamper 检查并对比 `encrypted_sha256`；被修改对象必须继续拒绝下载。
3. 恢复前先验证最近 same-host/offsite backup。
4. 尽量只恢复受影响对象，再重新做 integrity check。
5. 无法解释的修改按安全事故处理，并保留事发前后的外部 audit checkpoints。

### C. Credential/token 疑似泄露

1. 撤销受影响 server session；范围不明时撤销该账户全部 session。
2. 在对应 provider 轮换 DB/email/S3/HMAC credential，替换值不得写日志。
3. HMAC key 可能泄露时，保留所有旧 immutable checkpoints，轮换 key 并建立新的 key epoch；旧 checkpoint 仍用退役的离线 key 验证。
4. 用 ID/时间检查 auth rate-limit、fail2ban 和 audit 记录，不复制 token。

### D. Migration 失败 / Schema mismatch

1. 停止自动部署，让 backend 保持 not-ready。
2. 对比 `.mcs21-release`、Alembic head、`audit_chain_heads.schema_revision`。
3. 只能使用审核过的 migration/deploy 流程，不得通过 `stamp` 或直接改 metadata 掩盖 mismatch。
4. 无法立即兼容时回滚 code 到匹配 release；DB rollback 只走对应 migration 的审核恢复方案。

### E. Audit chain/checkpoint 失败

1. 立即冻结外部 checkpoint 删除，把相关序列只读复制到另一台机器。
2. 使用离线 key 执行 `audit_checkpoint.py --verify`，区分 HMAC 错误、序列倒退、外部对象缺失，或 DB head 与最新 anchor 不一致。
3. 运行应用 audit-chain verifier；保存证据前禁止“修复” chain row。
4. 最近一个通过验证的外部 checkpoint 是可信历史下界，无法与它衔接的 DB 历史必须升级处理。

### F. Recovery key 事故

1. reviewer/recovery key custody 可疑时暂停新的 recovery approval。
2. 排障时绝不能上传或邮件发送 recovery private key。
3. 检查 recovery audit 与脱敏 `recovery_operation` 事件，确认 requester/reviewer 分离及异常 rejection 峰值。
4. 通过审核过的 governance 流程替换受影响 recovery public key，并保留跨越该变更的 audit evidence/checkpoints。

## 7. 停用 / 回滚

Observability 不是真实业务状态；停用不会修改应用数据：

```bash
sudo systemctl disable --now mcs21-ops-monitor.timer mcs21-audit-checkpoint.timer
sudo systemctl stop mcs21-ops-monitor.service mcs21-audit-checkpoint.service || true
```

回滚 release 会移除 middleware/metrics endpoint，但**不得删除**已有外部 checkpoints，它们是历史证据。

## 8. #59 staging 证据记录

所有行用真实主机证据填完前不要关闭 #59：

| 项目 | 证据 |
|---|---|
| 已部署 merge SHA | `<待填>` |
| backend 仅绑定 loopback，trusted proxy 仅 127.0.0.1 | `<待填>` |
| `/internal/metrics` backend loopback 可达且 nginx 公网不可达 | `<待填>` |
| monitor 手动运行 / timer 已启用 | `<待填>` |
| 人为触发 monitor failure 后收到脱敏告警 | `<待填>` |
| 首个外部 checkpoint 目的地/object | `<待填>` |
| 第二台机器独立 HMAC 验证 | `<待填>` |
| log/alert secret-canary 扫描 | `<待填>` |
