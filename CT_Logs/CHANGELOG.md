# Changelog / 更新日志

All notable changes to this project are documented in this file.

本文件记录此项目的所有重要变更。

## [Unreleased] / [未发布]

### Email verification and password reset / 邮箱验证与密码重置

- Added the `email_verification_codes` table as Alembic revision
  `0004_email_verification_codes`, together with the matching production
  `02-schema.sql` DDL, runtime CRUD grant, and `03-verify.sql` expectations. A row stores
  only an HMAC-SHA-256 digest keyed by the server secret, purpose, and normalized address,
  never the emailed code, and CHECK constraints hold the expiry, attempt-bound, and
  `CONSUMED`/`consumed_at` invariants.
- 已新增 `email_verification_codes` 表（Alembic revision `0004_email_verification_codes`），
  并同步生产 `02-schema.sql` DDL、运行时 CRUD 授权及 `03-verify.sql` 核验期望。数据行只保存
  以服务端 secret、用途与规范化地址为密钥的 HMAC-SHA-256 摘要，绝不保存邮件中的验证码；
  CHECK 约束固定了过期时间、尝试次数上界及 `CONSUMED`/`consumed_at` 不变量。
- Widened the shared `auth_login_throttles` scope enum with four verification buckets so
  code sending and code checking are rate limited per address and per IP without a second
  rate-limit mechanism.
- 已扩展共享的 `auth_login_throttles` scope 枚举，新增四个验证码 bucket，使验证码的发送与
  校验按邮箱和 IP 分别限流，无需引入第二套限流机制。
- Added `POST /auth/verification-codes/send`, which answers identically whether or not the
  address has an account and consumes its rate-limit allowance either way, so it cannot be
  used to enumerate registered users.
- 已新增 `POST /auth/verification-codes/send`；无论地址是否已注册都返回相同响应并同样消耗
  限流额度，因此无法被用来枚举已注册用户。
- `POST /auth/register` now requires `verification_code` and stores the account with
  `email_verified` already true. Added `POST /auth/password-reset`, which consumes the code
  before judging the username/email pair, writes a new Argon2id hash, and revokes every
  session family. Reset leaves the key-protection profile and encrypted private-key bundle
  untouched, so an account never loses access to its encrypted files by resetting a
  forgotten login password.
- `POST /auth/register` 现在要求 `verification_code`，并直接以 `email_verified` 为真写入
  账户。已新增 `POST /auth/password-reset`：先消费验证码再判断用户名/邮箱是否匹配，写入新的
  Argon2id 哈希并撤销全部 Session family。重置不会改动密钥保护配置与加密私钥包，因此账户
  不会因为重置遗忘的登录密码而失去对已加密文件的访问能力。
- Fixed a defect found during end-to-end verification: a rejected code attempt was recorded
  in the caller's transaction, so the rollback that discarded the failed registration or
  reset also discarded the attempt counter and throttle updates, leaving a live code open to
  unlimited guessing. A rejected attempt now commits on its own before raising.
- 已修复端到端验证中发现的缺陷：被拒绝的验证码尝试原本记录在调用方事务中，导致丢弃失败注册或
  重置的那次回滚同时丢弃了尝试计数与限流更新，使仍然有效的验证码可被无限次猜测。现在被拒绝的
  尝试会先独立提交再抛出异常。
- Added outbound email delivery with selectable `resend` (HTTPS API), generic `smtp`, and
  development-only `console` providers, using only the Python standard library so the
  backend gains no new dependency. Production settings reject `console`, which never
  delivers mail.
- 已新增出站邮件投递，支持 `resend`（HTTPS API）、通用 `smtp` 及仅供开发的 `console` 三种
  provider，且只使用 Python 标准库，后端不新增任何依赖。生产配置会拒绝从不真正发信的
  `console`。

### Browser account-key enrolment / 浏览器账户密钥注册

- Replaced the registration page with the client-custody enrolment flow: the browser
  generates the RSA-3072 key pair and a random AMK, derives the KEK with Argon2id, wraps the
  AMK, encrypts the PKCS8-DER private key under an AMK/HKDF-derived key, and self-tests that
  both envelopes reopen before any account is created. The passphrase and plaintext private
  key never leave the browser; the private key is shown once for the user to save.
- 已将注册页替换为客户端托管的密钥注册流程：浏览器生成 RSA-3072 密钥对与随机 AMK，用
  Argon2id 派生 KEK 并包装 AMK，再用 AMK/HKDF 派生密钥加密 PKCS8-DER 私钥，并在创建账户前
  自测两个信封均可重新打开。Passphrase 与明文私钥绝不离开浏览器；私钥只展示一次供用户保存。
- The registration form now collects an encryption passphrase separate from the login
  password, as required by `docs/SECURITY_FLOWS.md`, and states that losing it makes the
  encrypted files unrecoverable.
- 注册表单现在按 `docs/SECURITY_FLOWS.md` 的要求收集独立于登录密码的加密 passphrase，并明确
  说明遗失后已加密文件不可恢复。
- Completed the previously non-functional reset-password page with code sending, a resend
  cooldown, and a success state that reports how many sessions were signed out.
- 已补全此前无法使用的重置密码页：支持发送验证码、重发冷却，并在成功后提示被登出的会话数量。
- Registration and login failures now surface the API's `message` and field-level validation
  detail instead of the bare "Request failed with status code 422" that axios produces by
  default. The 422 seen during testing was the frontend omitting the required `key_material`
  field, submitting a password below the 15-character minimum, and submitting an address
  without a top-level domain; it was never a database fault.
- 注册与登录失败现在会展示 API 返回的 `message` 及字段级校验详情，而不是 axios 默认产生的
  "Request failed with status code 422"。测试中出现的 422 源于前端漏发必填的 `key_material`
  字段、密码短于 15 个字符下限，以及邮箱缺少顶级域，与数据库无关。

### Verification / 验证

- Verified the complete production SQL path on disposable MySQL 8.4:
  `01-provision.sql -> 02-schema.sql -> 03-verify.sql` installs 16 application tables and
  reports every status `OK` with no deviation rows.
- 已在一次性 MySQL 8.4 上验证完整生产 SQL 路径：`01-provision.sql -> 02-schema.sql ->
  03-verify.sql` 安装 16 张应用表，所有状态均为 `OK`，无偏差行。
- Verified the development migration path on a separate empty MySQL 8.4 database:
  `0001 -> 0004` upgrade, `alembic check` parity, and a clean `0004 -> 0003 -> 0004`
  round trip. The first downgrade attempt failed because MySQL refuses to drop an index a
  foreign key depends on; the revision now drops the table first, which removes both.
- 已在另一个空 MySQL 8.4 数据库上验证开发迁移路径：`0001 -> 0004` 升级、`alembic check`
  一致性，以及干净的 `0004 -> 0003 -> 0004` 往返。首次降级失败是因为 MySQL 拒绝删除外键
  依赖的索引；该 revision 现在先删表，索引与外键随之一并移除。
- Backend verification: Ruff passes and the test suite reports `212 passed` with the MySQL
  integration tests actually running rather than skipped.
- 后端验证：Ruff 通过，测试套件 `212 passed`，且 MySQL 集成测试为真实执行而非跳过。
- Verified the full flow end to end over HTTP against MySQL, and again through a real
  browser: send code, reject a wrong code, register, reject a replayed code, log in, reset
  the password, and confirm the old password fails while the new one works and the key
  envelopes are unchanged.
- 已通过 HTTP 对 MySQL 完成端到端验证，并在真实浏览器中再次验证：发送验证码、拒绝错误验证码、
  注册、拒绝重放验证码、登录、重置密码，并确认旧密码失效、新密码可用且密钥信封未被改动。

### Deployment operations / 部署运维

- Fixed MySQL 8.4 verification false positives caused by the server rendering
  `OCTET_LENGTH` as `LENGTH` and adding character-set introducers and escaped quotes to stored
  CHECK clauses. The comparison still verifies the complete security-critical expressions.
- 修复 MySQL 8.4 对 CHECK 子句使用 `LENGTH` 同义形式、字符集前缀及转义引号而导致的核验
  误报；比较仍覆盖完整的安全关键约束表达式。
- Added the versioned server-pull automatic deployment command and systemd units for the
  MCS21 staging VPS. The timer deploys an exact `main` commit through the guarded release
  command and quarantines a failed SHA instead of retrying it continuously.
- 已加入 MCS21 预发布 VPS 的服务器拉取自动部署命令与 systemd 单元。Timer 会通过带保护措施
  的发布入口部署准确的 `main` commit，并隔离失败 SHA，避免持续重复部署坏版本。
- Documented the pull-request-to-release workflow, read-only Deploy Key boundary, operator
  commands, database safety boundary, rollback behavior, and audit path in English and Chinese.
- 已用中英文记录从 Pull Request 到发布的流程、只读 Deploy Key 边界、队员命令、数据库安全
  边界、回滚行为及审计路径。
- Versioned the guarded release implementation and fixed completed-release permissions so the
  unprivileged `fypapp` and Nginx identities can execute/read artifacts created after source
  extraction. The failed preflight remained on the prior healthy release and the corrected
  retry passed.
- 已将带保护措施的发布实现纳入版本管理，并修复完整 release 的最终权限，使无特权
  `fypapp` 与 Nginx 身份可执行／读取源码解压后才生成的文件。首次预检失败期间仍保持旧健康
  版本运行，修复后的重试已经通过。
- Treat scheduled skips of an already-quarantined SHA as a healthy no-op while retaining the
  original deployment failure in the journal and audit log.
- 已隔离 SHA 的后续定时跳过现在属于健康的无操作；原始部署失败仍保留在 journal 与审计日志
  中，不再每两分钟制造重复的 systemd 失败。

### Development environment / 开发环境

- Created the `CT-1.0` development branch for upcoming cryptography work.
- 已创建用于后续密码学工作的 `CT-1.0` 开发分支。
- Created the project-local Python virtual environment at `backend/.venv`.
- 已在 `backend/.venv` 创建项目本地 Python 虚拟环境。
- Installed the repository-pinned `pytest` 9.1.1 and `cryptography` 50.0.0 packages.
- 已安装仓库锁定版本的 `pytest` 9.1.1 和 `cryptography` 50.0.0。

### Scope note / 范围说明

- No application or cryptographic implementation code was changed in this update.
- 本次更新未修改应用程序代码或密码学实现代码。

update:2026/8/15 02:40

-------------------------------------------------------------------------------------------------------------
## CT-1.1

### Baseline / 基线

- Created `CT-1.1` from the merged `main` commit `9593e75`.
- 已从完成合并的 `main` 提交 `9593e75` 创建 `CT-1.1`。
- Verified the existing cryptography baseline with
  `python -m pytest tests/unit/test_crypto_service.py -q --durations=10`:
  4 tests passed in 0.54 seconds.
- 已使用 `python -m pytest tests/unit/test_crypto_service.py -q --durations=10`
  验证现有密码学基线：4 项测试全部通过，耗时 0.54 秒。

### Confirmed limitations / 已确认限制

- AES-GCM encryption currently processes the complete plaintext in memory and does not
  authenticate associated data (AAD).
- 当前 AES-GCM 加密会在内存中处理完整明文，且未认证关联数据（AAD）。
- No versioned encrypted-envelope format or streaming encryption interface exists yet.
- 当前尚无带版本的密文封装格式或流式加密接口。
- No cryptographic implementation code was changed during this baseline step.
- 本基线步骤未修改任何密码学实现代码。

update: 2026/8/12 17:27
