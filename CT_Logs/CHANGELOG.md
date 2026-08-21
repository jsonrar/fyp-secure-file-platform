# Changelog / 更新日志

All notable changes to this project are documented in this file.

本文件记录此项目的所有重要变更。

## How this file is organized / 本文件的组织方式

Two logs share this file, and they answer different questions.

- **[Unreleased]** is the release log: what changed in the product, grouped by area, in the
  order it landed on `main`.
- **Crypto track (CT) milestones** are per-work-package records. Each one names the `main`
  commit it branched from, the scope it stayed inside, and the limitations it confirmed but
  deliberately did not fix.

An entry belongs to whichever log matches the question it answers. Work that shipped a change
to the product goes in the release log even when the crypto track did it; a milestone record
stays a milestone record even when it changed no code.

本文件承载两份日志，回答的是不同的问题。

- **[未发布]** 是发布日志：产品发生了什么变化，按领域分组，按落到 `main` 的顺序排列。
- **密码学工作包里程碑（CT）** 是分工作包的记录。每一段都写明它从哪个 `main` 提交拉出、范围限定
  在哪里，以及确认存在但有意留待后续处理的限制。

条目归入哪一份，取决于它回答的是哪个问题。产品发生了变化就写进发布日志——即使这项工作出自密码学线；
里程碑记录仍然是里程碑记录——即使它没有改动任何代码。

## [Unreleased] / [未发布]

### Email verification and password reset / 邮箱验证与密码重置

- Reverted the registration path to client-held key custody after `c45e54d` had moved account-key generation onto the server and dropped `email` from the registration contract. The backend again accepts client-generated `key_material` and never sees a passphrase, AMK, or plaintext private key, as `docs/SECURITY_FLOWS.md` requires. `CryptoService.generate_account_key`, `derive_argon2id_key`, and their unit tests are kept in the tree, unused and marked as such, so the team can review the direction rather than lose the work.
- 在 `c45e54d` 把账户密钥生成移到服务端并从注册契约中移除 `email` 之后，已将注册路径恢复为客户端密钥托管。后端重新接收客户端生成的 `key_material`，并且不再接触 passphrase、AMK 或明文私钥，符合 `docs/SECURITY_FLOWS.md` 的要求。`CryptoService.generate_account_key`、`derive_argon2id_key` 及其单元测试予以保留（当前未被调用并已标注），供团队评审方向，而非直接删除队友的成果。
- Added the `email_verification_codes` table as Alembic revision `0004_email_verification_codes`, together with the matching production `02-schema.sql` DDL, runtime CRUD grant, and `03-verify.sql` expectations. A row stores only an HMAC-SHA-256 digest keyed by the server secret, purpose, and normalized address, never the emailed code, and CHECK constraints hold the expiry, attempt-bound, and `CONSUMED`/`consumed_at` invariants.
- 已新增 `email_verification_codes` 表（Alembic revision `0004_email_verification_codes`）， 并同步生产 `02-schema.sql` DDL、运行时 CRUD 授权及 `03-verify.sql` 核验期望。数据行只保存 以服务端 secret、用途与规范化地址为密钥的 HMAC-SHA-256 摘要，绝不保存邮件中的验证码； CHECK 约束固定了过期时间、尝试次数上界及 `CONSUMED`/`consumed_at` 不变量。
- Widened the shared `auth_login_throttles` scope enum with four verification buckets so code sending and code checking are rate limited per address and per IP without a second rate-limit mechanism.
- 已扩展共享的 `auth_login_throttles` scope 枚举，新增四个验证码 bucket，使验证码的发送与 校验按邮箱和 IP 分别限流，无需引入第二套限流机制。
- Added `POST /auth/verification-codes/send`, which answers identically whether or not the address has an account and consumes its rate-limit allowance either way, so it cannot be used to enumerate registered users.
- 已新增 `POST /auth/verification-codes/send`；无论地址是否已注册都返回相同响应并同样消耗 限流额度，因此无法被用来枚举已注册用户。
- `POST /auth/register` now requires `verification_code` and stores the account with `email_verified` already true. Added `POST /auth/password-reset`, which consumes the code before judging the username/email pair, writes a new Argon2id hash, and revokes every session family. Reset leaves the key-protection profile and encrypted private-key bundle untouched, so an account never loses access to its encrypted files by resetting a forgotten login password.
- `POST /auth/register` 现在要求 `verification_code`，并直接以 `email_verified` 为真写入 账户。已新增 `POST /auth/password-reset`：先消费验证码再判断用户名/邮箱是否匹配，写入新的 Argon2id 哈希并撤销全部 Session family。重置不会改动密钥保护配置与加密私钥包，因此账户 不会因为重置遗忘的登录密码而失去对已加密文件的访问能力。
- Fixed a defect found during end-to-end verification: a rejected code attempt was recorded in the caller's transaction, so the rollback that discarded the failed registration or reset also discarded the attempt counter and throttle updates, leaving a live code open to unlimited guessing. A rejected attempt now commits on its own before raising.
- 已修复端到端验证中发现的缺陷：被拒绝的验证码尝试原本记录在调用方事务中，导致丢弃失败注册或 重置的那次回滚同时丢弃了尝试计数与限流更新，使仍然有效的验证码可被无限次猜测。现在被拒绝的 尝试会先独立提交再抛出异常。
- Added outbound email delivery with selectable `resend` (HTTPS API), generic `smtp`, and development-only `console` providers, using only the Python standard library so the backend gains no new dependency. Production settings reject `console`, which never delivers mail.
- 已新增出站邮件投递，支持 `resend`（HTTPS API）、通用 `smtp` 及仅供开发的 `console` 三种 provider，且只使用 Python 标准库，后端不新增任何依赖。生产配置会拒绝从不真正发信的 `console`。

### Browser account-key enrolment / 浏览器账户密钥注册

- Replaced the registration page with the client-custody enrolment flow: the browser generates the RSA-3072 key pair and a random AMK, derives the KEK with Argon2id, wraps the AMK, encrypts the PKCS8-DER private key under an AMK/HKDF-derived key, and self-tests that both envelopes reopen before any account is created. The passphrase and plaintext private key never leave the browser; the private key is shown once for the user to save.
- 已将注册页替换为客户端托管的密钥注册流程：浏览器生成 RSA-3072 密钥对与随机 AMK，用 Argon2id 派生 KEK 并包装 AMK，再用 AMK/HKDF 派生密钥加密 PKCS8-DER 私钥，并在创建账户前 自测两个信封均可重新打开。Passphrase 与明文私钥绝不离开浏览器；私钥只展示一次供用户保存。
- Removed twelve labels from the client key contract. `key_material` carried algorithm names, format and AAD versions, and the derived key length — twelve fields with exactly one legal value each, which a caller could only repeat back or get a `422` for varying. The API supplies them now, taking the request from 29 leaf fields to 17. Nothing about the cryptography changed: `to_domain()` fills the same values, so stored rows, `*Out` responses, and the RSA-PSS current-key authorization payload are byte-for-byte what they were, and no signing-payload version bump was needed. The KDF cost parameters stay on the wire because they are a per-account choice that lets the cost be raised later without locking out existing accounts, `key_size_bits` stays because it has three legal values and is cross-checked against the modulus of the uploaded key, and `ciphertext_sha256` stays because it is the commitment the authorization signature carries. New unit tests pin both halves: the wire form must rebuild the fully labelled domain object, and each removed field must be rejected as an unexpected field so the boilerplate cannot creep back one line at a time.
- 已从客户端密钥契约中移除十二个标签字段。`key_material` 原本携带算法名、格式版本与 AAD 版本、派生密钥长度——这十二个字段各自只有一个合法取值，调用方要么原样重复，要么因改动而得到 `422`。现在由 API 自行提供，请求从 29 个叶子字段降到 17 个。密码学部分没有任何变化：`to_domain()` 填入完全相同的值，因此存储行、`*Out` 响应以及 RSA-PSS 当前密钥授权载荷逐字节不变，也无需升级签名载荷版本。KDF 开销参数保留在请求中，因为它是按账户的选择，正是它使得日后调高开销而不锁死老账户成为可能；`key_size_bits` 保留，因为它有三个合法取值且会与上传公钥的模数交叉核对；`ciphertext_sha256` 保留，因为它是授权签名所承诺的那个摘要。新增单元测试固定了两端：请求形态必须能重建带全部标签的领域对象，且每个被移除的字段都必须作为多余字段被拒绝，使这些样板无法一行一行地长回来。
- The registration form now collects an encryption passphrase separate from the login password, as required by `docs/SECURITY_FLOWS.md`, and states that losing it makes the encrypted files unrecoverable.
- 注册表单现在按 `docs/SECURITY_FLOWS.md` 的要求收集独立于登录密码的加密 passphrase，并明确 说明遗失后已加密文件不可恢复。
- Completed the previously non-functional reset-password page with code sending, a resend cooldown, and a success state that reports how many sessions were signed out.
- 已补全此前无法使用的重置密码页：支持发送验证码、重发冷却，并在成功后提示被登出的会话数量。
- Registration and login failures now surface the API's `message` and field-level validation detail instead of the bare "Request failed with status code 422" that axios produces by default. The 422 seen during testing was the frontend omitting the required `key_material` field, submitting a password below the 15-character minimum, and submitting an address without a top-level domain; it was never a database fault.
- 注册与登录失败现在会展示 API 返回的 `message` 及字段级校验详情，而不是 axios 默认产生的 "Request failed with status code 422"。测试中出现的 422 源于前端漏发必填的 `key_material` 字段、密码短于 15 个字符下限，以及邮箱缺少顶级域，与数据库无关。

### Verification / 验证

- Verified the deployed staging build end to end at `https://secureview.tech`: the send endpoint answers `200` and stores only a digest, an unregistered address for password reset answers `200` with no row written, a resend inside the cooldown answers `429` with `Retry-After`, and a real verification email reached a Gmail inbox rather than the spam folder.
- 已在 `https://secureview.tech` 上对已部署版本完成端到端验证：发送端点返回 `200` 且只存摘要；未注册地址请求重置码返回 `200` 且不写入任何数据行；冷却期内重发返回 `429` 并带 `Retry-After`；真实验证码邮件送达 Gmail 收件箱而非垃圾箱。

- Verified the complete production SQL path on disposable MySQL 8.4: `01-provision.sql -> 02-schema.sql -> 03-verify.sql` installs 16 application tables and reports every status `OK` with no deviation rows.
- 已在一次性 MySQL 8.4 上验证完整生产 SQL 路径：`01-provision.sql -> 02-schema.sql -> 03-verify.sql` 安装 16 张应用表，所有状态均为 `OK`，无偏差行。
- Verified the development migration path on a separate empty MySQL 8.4 database: `0001 -> 0004` upgrade, `alembic check` parity, and a clean `0004 -> 0003 -> 0004` round trip. The first downgrade attempt failed because MySQL refuses to drop an index a foreign key depends on; the revision now drops the table first, which removes both.
- 已在另一个空 MySQL 8.4 数据库上验证开发迁移路径：`0001 -> 0004` 升级、`alembic check` 一致性，以及干净的 `0004 -> 0003 -> 0004` 往返。首次降级失败是因为 MySQL 拒绝删除外键 依赖的索引；该 revision 现在先删表，索引与外键随之一并移除。
- Backend verification: Ruff passes and the test suite reports `225 passed` with the MySQL integration tests actually running rather than skipped. The frontend suite reports `99 passed`, of which 14 cover the account-key enrolment module.
- 后端验证：Ruff 通过，测试套件 `225 passed`，且 MySQL 集成测试为真实执行而非跳过。前端测试 `99 passed`，其中 14 项覆盖账户密钥登记模块。
- Verified the full flow end to end over HTTP against MySQL, and again through a real browser: send code, reject a wrong code, register, reject a replayed code, log in, reset the password, and confirm the old password fails while the new one works and the key envelopes are unchanged.
- 已通过 HTTP 对 MySQL 完成端到端验证，并在真实浏览器中再次验证：发送验证码、拒绝错误验证码、 注册、拒绝重放验证码、登录、重置密码，并确认旧密码失效、新密码可用且密钥信封未被改动。

### Deployment operations / 部署运维

- Served the staging VPS over HTTPS at `secureview.tech` with a Let's Encrypt certificate, an HTTP-to-HTTPS redirect, and a one-year `Strict-Transport-Security` header. This is a functional requirement rather than a cosmetic one: browsers expose `crypto.subtle` only in a secure context, so client-side account-key enrolment cannot run over plain HTTP. The live server block is now tracked as `deployment/server/nginx-secureview.conf`, and `docs/DEPLOYMENT.md` gained a TLS section.
- 已为预发布 VPS 启用 HTTPS（`secureview.tech`，Let's Encrypt 证书、HTTP 到 HTTPS 跳转、一年期 `Strict-Transport-Security` 头）。这是功能性要求而非装饰：浏览器只在安全上下文中暴露 `crypto.subtle`，客户端账户密钥登记在明文 HTTP 下无法运行。线上 server 块已纳入版本管理（`deployment/server/nginx-secureview.conf`），`docs/DEPLOYMENT.zh-CN.md` 新增 TLS 章节。
- Kept the two release probes reachable on port 80 from loopback only, after certbot's generated redirects made `mcs21-deploy` fail its post-deploy live health check and roll the release back. The probes use a bare-IP `Host` header that the domain redirects do not match, so they answered `404`. External clients on the bare IP over cleartext still get `403`.
- 在 certbot 生成的跳转导致 `mcs21-deploy` 部署后存活检查失败并回滚之后，已让两个发布探针在 80 端口仅对回环地址可达。探针使用裸 IP 的 `Host` 头，与域名跳转不匹配，因而返回 `404`。外部客户端以明文访问裸 IP 仍返回 `403`。
- Redirected the rest of port 80 to `https://secureview.tech`, the bare IP included. The loopback-only probe exception above left every other cleartext path answering nginx's own `404`, so a teammate who reached the box by address saw a bare "404 Not Found" page and read it as a dead backend while the service was serving normally. Loopback keeps its `200` for the release gate; the `403` an external client used to get is now that same redirect, and still nothing crosses the wire in cleartext. The redirect is `308` so that a cleartext `POST` to `/api/` keeps its method and body rather than arriving as a `GET` and failing with `405`. The 443 block does answer on the bare IP, but the certificate covers only the two host names and Let's Encrypt does not issue for IP addresses, so the address is a way in rather than a way to browse.
- 已将 80 端口的其余请求跳转至 `https://secureview.tech`，裸 IP 也不例外。上一条的回环专用探针例外，使得其余所有明文路径都由 nginx 返回自带的 `404`；队友以 IP 访问时看到一个光秃秃的 "404 Not Found" 页面，误以为后端挂了，而服务其实一直正常。回环仍返回 `200` 以满足发布门禁；外部客户端原本得到的 `403` 现在变成同一个跳转，且仍然没有任何内容以明文传输。跳转使用 `308`，使明文 `POST` 到 `/api/` 时保留方法与请求体，而不是变成 `GET` 后以 `405` 失败。443 端口块确实也在裸 IP 上响应，但证书只覆盖两个域名，且 Let's Encrypt 不为 IP 签发证书——因此该地址是入口，而不是浏览方式。
- Fixed the live audit-head revision in the release gate. Merging PR #9's live audit-chain check together with revision `0004` updated only the genesis branch of the singleton query; the live branch still required `0003_client_key_custody`, so a staging database that legitimately holds audit rows matched neither branch, reported `REVIEW`, and quarantined the release. The database itself was consistent throughout. The unit test now asserts the exact occurrence count and that no stale revision string survives, because checking only that the current revision appears somewhere is what let the half-updated query through.
- 已修复发布门禁中在线审计链头的 revision。将 PR #9 的在线审计校验与 revision `0004` 合并时只更新了单例查询的 genesis 分支，live 分支仍要求 `0003_client_key_custody`，导致合法含有审计记录的预发布数据库两个分支都不匹配、判定为 `REVIEW` 并隔离发布；数据库本身自始至终一致。单元测试现在断言精确出现次数并要求不残留旧 revision 字符串——此前只检查「当前 revision 出现过」，正是这一点放过了半更新的查询。
- Restored `email-validator`, which `c45e54d` had removed along with the email field it no longer used. Bringing back client-held key custody reintroduced `EmailStr`, whose import fails without it. Every local test still passed because developer virtual environments retained the package from an earlier install; only the release preflight, which builds its venv from `requirements.txt` alone, could surface the gap. A unit test now ties the declaration to the actual use of `EmailStr`.
- 已恢复 `email-validator`——`c45e54d` 在移除不再使用的 email 字段时将其一并删除。恢复客户端密钥托管后重新引入的 `EmailStr` 在缺少该依赖时无法导入。本地测试全部通过，是因为开发者虚拟环境中残留着早先安装的该包；只有依据 `requirements.txt` 独立构建 venv 的发布预检能暴露此缺口。现已新增单元测试，将依赖声明与 `EmailStr` 的实际使用绑定。
- Set an explicit `User-Agent` on Resend API requests. Every verification email failed with a provider `403` while the identical payload and API key succeeded from `curl` on the same host; Resend's edge blocks urllib's default `Python-urllib/<version>` agent before the request reaches the API. The provider's error name is now logged next to the status, since a bare `403` gave no way to separate a blocked agent from a bad key, while the response body cannot be logged because it can echo the recipient address.
- 已为 Resend API 请求设置显式 `User-Agent`。此前所有验证码邮件都因 provider 返回 `403` 而失败，而完全相同的 payload 与 API key 在同一主机上用 `curl` 却成功——Resend 的边缘层在请求到达 API 之前拦截了 urllib 默认的 `Python-urllib/<版本>` UA。现在会在状态码旁记录 provider 的错误名称：仅有 `403` 无法区分「UA 被拦」与「密钥错误」，而响应体不能记录，因为其中可能回显收件人地址。
- Added `backend/scripts/seed_test_account.py`, which seeds a shared staging login for frontend development. Account keys are client-held, so a fixture cannot be written by hand: the passphrase has to open an Argon2id-wrapped AMK and an HKDF/AES-GCM-sealed PKCS#8 key that only the browser ever built. The script rebuilds that enrolment in Python against `frontend/src/utils/account-crypto.ts`, plants the verification code so no mail is sent, and then calls `AuthService.register` itself, audit entry included. It self-tests that both envelopes reopen from the passphrase alone before writing, and validates the identifiers through `UserRegisterRequest`, because `register()` takes plain strings and an address on a reserved TLD such as `.test` registers cleanly and then makes every login return `500` when `AuthUserResponse` refuses to serialize it back — which is exactly what the first seeded account did. Cross-language compatibility was confirmed by feeding the live `/keys/me` envelope to the frontend's own crypto module under vitest and matching the recovered private key against the stored public key.
- 已新增 `backend/scripts/seed_test_account.py`，为前端开发种下一个共享的 staging 登录账号。账户密钥由客户端托管，夹具无法手写：密码短语必须能打开 Argon2id 包裹的 AMK 与 HKDF/AES-GCM 封装的 PKCS#8 私钥，而这套信封此前只有浏览器会生成。该脚本以 `frontend/src/utils/account-crypto.ts` 为准在 Python 侧复刻这一登记过程，直接种下验证码因而不发邮件，再调用 `AuthService.register` 本身，审计记录一并写入。写库之前它会自检两层信封仅凭密码短语即可重新打开，并让标识符先过 `UserRegisterRequest`——因为 `register()` 接收纯字符串，而保留 TLD（如 `.test`）的邮箱能顺利注册，随后 `AuthUserResponse` 拒绝将其序列化回去，使每一次登录都返回 `500`；第一个种下的账号正是如此。跨语言一致性已通过在 vitest 下把线上 `/keys/me` 信封交给前端自己的加密模块、并将还原出的私钥与库中公钥比对来确认。

- Distinguished a valid live audit chain (`LIVE_DATA`) from a fresh genesis state (`OK`) in the read-only MySQL deployment verifier. Live deployment still requires the singleton head to target the newest audit row with a matching hash and the exact Schema revision; `REVIEW`, `MISSING`, and `UNEXPECTED` continue to block releases. This fixes the false quarantine of frontend commit `acd0c9733eeb` without deleting audit evidence or bypassing the database gate.
- 在 MySQL 只读部署核验中区分有效在线审计链（`LIVE_DATA`）与全新初始状态（`OK`）。在线部署仍要求单例链头指向最新审计记录、哈希一致并保留准确的 Schema revision；`REVIEW`、`MISSING` 与 `UNEXPECTED` 仍会阻止发布。该修复解除前端提交 `acd0c9733eeb` 的误隔离，不会删除审计证据，也不会绕过数据库门禁。
- Fixed MySQL 8.4 verification false positives caused by the server rendering `OCTET_LENGTH` as `LENGTH` and adding character-set introducers and escaped quotes to stored CHECK clauses. The comparison still verifies the complete security-critical expressions.
- 修复 MySQL 8.4 对 CHECK 子句使用 `LENGTH` 同义形式、字符集前缀及转义引号而导致的核验误报；比较仍覆盖完整的安全关键约束表达式。
- Added the versioned server-pull automatic deployment command and systemd units for the MCS21 staging VPS. The timer deploys an exact `main` commit through the guarded release command and quarantines a failed SHA instead of retrying it continuously.
- 已加入 MCS21 预发布 VPS 的服务器拉取自动部署命令与 systemd 单元。Timer 会通过带保护措施的发布入口部署准确的 `main` commit，并隔离失败 SHA，避免持续重复部署坏版本。
- Documented the pull-request-to-release workflow, read-only Deploy Key boundary, operator commands, database safety boundary, rollback behavior, and audit path in English and Chinese.
- 已用中英文记录从 Pull Request 到发布的流程、只读 Deploy Key 边界、队员命令、数据库安全边界、回滚行为及审计路径。
- Versioned the guarded release implementation and fixed completed-release permissions so the unprivileged `fypapp` and Nginx identities can execute/read artifacts created after source extraction. The failed preflight remained on the prior healthy release and the corrected retry passed.
- 已将带保护措施的发布实现纳入版本管理，并修复完整 release 的最终权限，使无特权 `fypapp` 与 Nginx 身份可执行／读取源码解压后才生成的文件。首次预检失败期间仍保持旧健康版本运行，修复后的重试已经通过。
- Treat scheduled skips of an already-quarantined SHA as a healthy no-op while retaining the original deployment failure in the journal and audit log.
- 已隔离 SHA 的后续定时跳过现在属于健康的无操作；原始部署失败仍保留在 journal 与审计日志中，不再每两分钟制造重复的 systemd 失败。

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
## Crypto track (CT) milestones / 密码学工作包里程碑

Work-package records from the crypto track, oldest first. These are not release entries: a
milestone can close with no code changed, and the limitations it lists are left open on
purpose for a later package.

密码学线的工作包记录，按时间正序。它们不是发布条目：一个工作包可以在未改动代码的情况下结束，
其中列出的限制也是有意留给后续工作包的。

### CT-1.1

#### Baseline / 基线

- Created `CT-1.1` from the merged `main` commit `9593e75`.
- 已从完成合并的 `main` 提交 `9593e75` 创建 `CT-1.1`。
- Verified the existing cryptography baseline with `python -m pytest tests/unit/test_crypto_service.py -q --durations=10`: 4 tests passed in 0.54 seconds.
- 已使用 `python -m pytest tests/unit/test_crypto_service.py -q --durations=10` 验证现有密码学基线：4 项测试全部通过，耗时 0.54 秒。

#### Confirmed limitations / 已确认限制

- AES-GCM encryption currently processes the complete plaintext in memory and does not authenticate associated data (AAD).
- 当前 AES-GCM 加密会在内存中处理完整明文，且未认证关联数据（AAD）。
- No versioned encrypted-envelope format or streaming encryption interface exists yet.
- 当前尚无带版本的密文封装格式或流式加密接口。
- No cryptographic implementation code was changed during this baseline step.
- 本基线步骤未修改任何密码学实现代码。

update: 2026/8/12 17:27

-------------------------------------------------------------------------------------------------------------
### CT-1.2

Base `main` @ `c45e54d` · Scope: file encryption only · No backend changes
基线 `main` @ `c45e54d` · 范围：仅文件加密 · 未改动后端

#### Added / 新增

- `frontend/src/crypto/encoding.ts` — byte encoding: integers, UUIDs, NFC-normalized UTF-8, canonical Base64, length prefixes.
- `frontend/src/crypto/encoding.ts` — 字节编码：整数、UUID、NFC 归一化 UTF-8、规范 Base64、长度前缀。
- `frontend/src/crypto/primitives.ts` — AES-256-GCM (detached tag), SHA-256, RSA-OAEP-SHA256, RSA-PSS-SHA256.
- `frontend/src/crypto/primitives.ts` — AES-256-GCM（分离 tag）、SHA-256、RSA-OAEP-SHA256、RSA-PSS-SHA256。
- `docs/crypto/test_vectors.json` and 41 vitest cases. Vectors are generated with `python-cryptography`, so the TypeScript is checked against an independent implementation rather than against itself.
- `docs/crypto/test_vectors.json` 与 41 项 vitest 用例。向量由 `python-cryptography` 生成，使 TypeScript 对照独立实现验证，而非自我往返验证。
- `vitest` declared in `package.json` with `package-lock.json` synchronized.
- 已在 `package.json` 声明 `vitest`，并同步 `package-lock.json`。

#### Why / 用途

The frontend had no encryption at all; uploads sent plaintext. These are the primitives every
encrypted upload needs: ciphertext, nonce, tag, and RSA-wrapped keys.
前端此前没有任何加密，上传发送的是明文。这些是每次加密上传都需要的底层原语：密文、nonce、tag 与 RSA 包装的密钥。

Three rules the backend already enforces are now caught by tests instead of at runtime:
三条后端已在强制、但此前无人知晓的规则，现在由测试拦截，而不是等到运行时才发现：

- The GCM tag must be detached from the ciphertext, or the upload is rejected.
- GCM tag 必须与密文分离，否则上传被拒。
- Base64 must be standard and padded, or the request is rejected.
- Base64 必须是标准字母表且带填充，否则请求被拒。
- Filenames must be NFC-normalized, or upload succeeds and later decryption fails.
- 文件名必须 NFC 归一化，否则上传成功、之后解密失败。

#### Not included / 未包含

- Argon2id and the account-key envelopes, while the key-custody model is unresolved on `main`.
- Argon2id 与账户密钥信封 —— `main` 上的密钥托管模型尚未定论。
- File envelope assembly and AAD construction, which follow in the next step.
- 文件信封组装与 AAD 构造，将在下一步完成。

#### Notes / 说明

- The existing `file_api.upload` is broken independently of this work: it posts the plaintext file to `/files/upload`, while the backend serves `POST /files` and requires ciphertext plus a metadata envelope.
- 现有 `file_api.upload` 本身即为损坏状态，与本次工作无关：它把明文文件发往 `/files/upload`，而后端提供的是 `POST /files`，且要求密文加元数据信封。
- `vue-tsc` cannot run here; it has drifted from the installed `typescript`. Used `tsc --noEmit` instead. Pre-existing.
- `vue-tsc` 在此无法运行，与已安装的 `typescript` 版本漂移。改用 `tsc --noEmit`。该问题早于本分支存在。

update: 2026/8/20

-------------------------------------------------------------------------------------------------------------
### CT-1.3

Base `main` @ `98f4c64` · Scope: file encryption envelope · No backend changes
基线 `main` @ `98f4c64` · 范围：文件加密信封 · 未改动后端

#### Added / 新增

- `frontend/src/crypto/file_envelope.ts` — AAD-3 construction, `encryptFile` / `decryptFile`, DEK wrapping to the owner and recovery keys, and the `POST /files` metadata assembly.
- `frontend/src/crypto/file_envelope.ts` — AAD-3 构造、`encryptFile` / `decryptFile`、DEK 向所有者与恢复密钥的包装，以及 `POST /files` 元数据组装。
- `docs/crypto/FILE_ENVELOPE.md` and its Chinese translation: the normative byte layout.
- `docs/crypto/FILE_ENVELOPE.md` 及其中文译本：规范性字节布局。
- 8 new reference vectors (6 AAD, 2 full envelopes) and 44 tests. 85 tests pass in total.
- 新增 8 组参考向量（6 组 AAD、2 组完整信封）与 44 项测试。累计 85 项测试通过。

#### Design decisions / 设计决策

- AAD-3 binds `file_id`, `envelope_version`, `plaintext_size`, `original_filename` and `mime_type`. Those last three are cleartext columns the server could otherwise rewrite, so binding them turns any such edit into a decryption failure.
- AAD-3 绑定 `file_id`、`envelope_version`、`plaintext_size`、`original_filename` 与 `mime_type`。后三者是服务器本可随意改写的明文列，绑定后任何此类修改都会变成解密失败。
- Trade-off: those three fields become immutable for the lifetime of the ciphertext. No rename route exists today, but a future one needs re-encryption or `envelope_version = 2`.
- 代价：这三个字段在密文生命周期内不可变。当前不存在改名路由，但将来若要支持，需要重新加密或升级到 `envelope_version = 2`。
- AAD-3 contains nothing per-recipient. The owner and every share recipient decrypt the same ciphertext with the same DEK, so binding `key_id` would break sharing entirely.
- AAD-3 不含任何按接收方变化的字段。所有者与每个共享接收方使用同一 DEK 解密同一密文，绑定 `key_id` 会彻底破坏共享。
- `encryptFile` self-tests by decrypting its own output before returning. The server cannot check that ciphertext decrypts to anything, so an unopenable envelope would otherwise be discovered only after the plaintext was gone.
- `encryptFile` 在返回前解密自己的输出进行自检。服务器无法验证密文能否解出内容，否则一个打不开的信封只会在明文丢弃之后才被发现。

#### Notes / 说明

- The server never computes this AAD, so no server-side check can catch a divergent second implementation; it would simply produce files nobody can decrypt. Hence the normative doc and the locked vectors.
- 服务器从不计算此 AAD，因此没有任何服务端检查能发现第二个实现的分歧，后果只是产出谁也解不开的文件。规范文档与锁定的向量正是为此而存在。
- The recovery wrapping remains unverifiable by any client; `buildUploadPayload` returns the locally recomputed recovery-key fingerprint so the caller can pin it.
- 恢复包装对任何客户端都不可验证；`buildUploadPayload` 会返回本地重算的恢复密钥指纹，供调用方固定比对。

#### Not included / 未包含

- Wiring into `file_api.ts` and the upload page, which still send plaintext.
- 接入 `file_api.ts` 与上传页面 —— 它们目前仍在发送明文。
- Argon2id and the account-key envelopes, while the key-custody model is unresolved.
- Argon2id 与账户密钥信封 —— 密钥托管模型尚未定论。

update: 2026/8/20

-------------------------------------------------------------------------------------------------------------
### CT-1.4

Base `main` @ `2003e47` · Scope: wire encryption into the upload path · No backend changes
基线 `main` @ `2003e47` · 范围：将加密接入上传路径 · 未改动后端

#### Fixed / 修复

- The upload page returned a bare `422`. `POST /files/upload` takes two multipart parts, `file` and `metadata`, and the page sent only `file` — with the plaintext in it. `metadata` is a required form field that cannot be filled without encrypting first, so FastAPI rejected every upload.
- 上传页此前直接返回 `422`。`POST /files/upload` 需要 `file` 与 `metadata` 两个 multipart 部分，而页面只发送了 `file`，且内容是明文。`metadata` 是必填字段，不先加密就无法填写，因此 FastAPI 拒绝了每一次上传。
- Removed the `AES-128 / AES-192 / AES-256 / 3DES` selector, which was wired to nothing, and the "Server-side encryption uses AES-256-GCM" copy, which described the opposite of the design.
- 已移除未接任何逻辑的 `AES-128 / AES-192 / AES-256 / 3DES` 下拉框，以及与设计相反的
  "Server-side encryption uses AES-256-GCM" 文案。
- Dropped the manual `Content-Type: multipart/form-data` header. Naming the type without a boundary leaves the browser unable to generate one.
- 已移除手写的 `Content-Type: multipart/form-data` 头。只写类型而不带 boundary 会导致浏览器无法生成分隔符。

#### Added / 新增

- `frontend/src/crypto/upload.ts` — fetches the owner and recovery public keys, encrypts the file, wraps the file key to both, and assembles the multipart payload.
- `frontend/src/crypto/upload.ts` — 获取所有者与恢复公钥、加密文件、将文件密钥包装给两者，并组装 multipart 载荷。
- `frontend/src/api/key_api.ts` — `GET /keys/me`, `/keys/me/{key_id}`, `/keys/users/{user_id}/active`.
- `frontend/src/api/key_api.ts` — `GET /keys/me`、`/keys/me/{key_id}`、`/keys/users/{user_id}/active`。
- `recovery_api.getPublicKey` for the active recovery key, and `fileApi.uploadEncrypted`.
- `recovery_api.getPublicKey` 用于获取活跃恢复密钥，以及 `fileApi.uploadEncrypted`。
- 9 tests, including a full round trip: unwrap the file key with a real RSA private key, rebuild the AAD from the metadata, and decrypt back to the exact input bytes. 109 tests pass in total.
- 新增 9 项测试，含完整往返验证：用真实 RSA 私钥解包文件密钥、从 metadata 重建 AAD、解密回完全一致的输入字节。累计 109 项测试通过。

#### Behaviour / 行为

- Recipient keys are fetched once per batch, not per file, and each file reports its own outcome so one rejected filename does not hide the uploads that succeeded.
- 接收方密钥按批次获取一次而非每个文件一次；每个文件单独报告结果，避免一个被拒的文件名掩盖其他成功的上传。
- The recovery key fingerprint is recomputed locally from the PEM and shown in the UI. It is never read from the API response field, because this is the one wrapping no client can verify.
- 恢复密钥指纹由客户端从 PEM 本地重算并在界面显示，绝不读取 API 响应中的该字段 —— 因为这是唯一无法被任何客户端验证的包装。
- Files above the 25 MiB limit are rejected before being read into memory, and `File.type` falls back to `application/octet-stream` when the browser reports nothing usable.
- 超过 25 MiB 限制的文件在读入内存前即被拒绝；当浏览器未能识别类型时，`File.type` 回退为 `application/octet-stream`。

#### Verified end to end / 端到端验证

- Ran against a local MySQL 8.4 and backend: `01/02/03` SQL reports schema `OK` at revision `0004`, two files uploaded and accepted, each with an owner and a recovery wrapping, and `file_size_bytes == encrypted_size_bytes` confirming the tag stayed detached.
- 已在本地 MySQL 8.4 与后端上运行：`01/02/03` SQL 报告 schema `OK`、revision 为 `0004`；两个文件上传成功并被接受，各带所有者与恢复两份包装；`file_size_bytes == encrypted_size_bytes`，证明 tag 保持分离。
- Decrypted a stored file with the **offline recovery private key**, rebuilding AAD-3 in Python from the persisted metadata alone. This path touches none of the TypeScript, so it independently confirms both the AAD byte layout and the recovery wrapping — the one envelope no client can ever self-test.
- 已用**离线恢复私钥**解密一个已存储的文件，且仅凭数据库中持久化的元数据在 Python 侧重建 AAD-3。该路径完全不经过 TypeScript，因此独立确认了 AAD 字节布局与恢复包装 —— 后者是任何客户端都无法自检的唯一信封。
- Added `upload.integration.test.ts`, skipped unless `E2E_API_BASE` is set, so `npm test` stays offline while the live check stays reproducible.
- 已新增 `upload.integration.test.ts`，未设置 `E2E_API_BASE` 时自动跳过，使 `npm test` 保持离线，同时让线上检查可复现。

update: 2026/8/20

-------------------------------------------------------------------------------------------------------------
### CT-1.5

Base `main` @ `8e174c6` · Scope: recovery key provisioning · No application code changed
基线 `main` @ `8e174c6` · 范围：恢复密钥的配置工具 · 未修改应用代码

#### Added / 新增

- `backend/scripts/register_recovery_key.py` — generates an RSA recovery key pair, writes the private half locally at mode 600, and registers only the public half through the ADMIN-only API route.
- `backend/scripts/register_recovery_key.py` — 生成 RSA 恢复密钥对，将私钥以 600 权限写入本地，并仅通过 ADMIN 专用 API 路由注册公钥。

#### Why / 用途

- Every upload wraps its file key twice: to the owner's public key and to the active recovery public key. With no recovery key registered, the API answers `No active recovery public key is configured` and nothing can be uploaded. Staging hit exactly this after the browser-side encryption landed.
- 每次上传都会把文件密钥包装两次：给所有者公钥和给活跃的恢复公钥。若未注册恢复密钥，API 返回 `No active recovery public key is configured`，任何文件都无法上传。浏览器端加密上线后，staging 正是卡在这里。

#### Safeguards / 保护措施

- Refuses to overwrite an existing private key file. Registering a new key revokes the previous one for new uploads but does not rewrap existing files, so the old private half must be retained.
- 拒绝覆盖已存在的私钥文件。注册新密钥会使旧密钥对新上传失效，但不会重新包装已有文件，因此旧私钥必须保留。
- Checks the account is `ADMIN` before generating anything, so a failed attempt leaves no key material behind.
- 在生成任何密钥材料之前先校验账号为 `ADMIN`，使失败的尝试不会遗留密钥材料。
- Compares the fingerprint the API reports against one computed locally and aborts on any difference.
- 将 API 返回的指纹与本地计算结果比对，不一致即中止。

#### Verified / 验证

- Ran against the local backend: rotation moved the previous key to `REVOKED`, a new upload wrapped to the new key, and the new private half decrypted the stored ciphertext. Both guards were exercised and neither wrote a private key on failure.
- 已对本地后端运行：轮换将旧密钥置为 `REVOKED`，新上传包装给新密钥，新私钥成功解密已存储的密文。两道保护均已触发，且失败时都未写出私钥。

#### Note / 说明

- The private key is not in offline or HSM custody, as `docs/SECURITY_FLOWS.md` describes for a real deployment. For this demonstration project it lives in `recovery_keys/`, which is gitignored in a private repository. Whoever holds it can decrypt every file uploaded under the matching public key.
- 本项目的私钥并未如 `docs/SECURITY_FLOWS.md` 对真实部署所述那样置于离线或 HSM 保管中。作为展示项目，它存放在 `recovery_keys/`（私有仓库中已被 gitignore）。持有该私钥者可解密以对应公钥上传的每一个文件。

update: 2026/8/20
