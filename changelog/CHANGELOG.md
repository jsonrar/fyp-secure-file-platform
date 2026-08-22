# Changelog / 更新日志

Every notable change to this project, from all of us, in one place. If you want to know what
the project did before you joined a piece of it, read this file top to bottom.

Add an entry in the section that matches the area you changed, as a pair of lines: English
first, then 简体中文. Say what changed and why it mattered — a reader six weeks from now
cannot recover the reason from the diff. Work-package records that did not ship a change to
the product belong in [`work-packages/`](work-packages/) instead; see
[`README.md`](README.md).

本项目所有重要变更的唯一汇总，来自我们每个人。想知道某块工作在你接手之前发生过什么，从头读这份
文件即可。

请在与改动领域对应的小节下追加条目，一条英文、一条简体中文成对出现。写清楚改了什么、以及为什么
重要——六周后的读者无法从 diff 里还原当时的理由。没有交付到产品里的工作包记录请写进
[`work-packages/`](work-packages/)，参见 [`README.md`](README.md)。

## [Unreleased] / [未发布]

### Password policy and registration form / 密码策略与注册表单

- Lowered the login-password minimum from 15 characters to 8, and paid for the difference with composition: a password must now draw on at least 2 of uppercase letters, lowercase letters, numbers, and symbols. Fifteen characters with no other rule was the worst of both trades — long enough to push people toward reuse or a sticky note, but still satisfied by `aaaaaaaaaaaaaaa`. Characters are bucketed by Unicode general category, so a non-Latin password is judged by the same rule rather than failing for being non-ASCII. Existing accounts are unaffected: the login and change-password endpoints still accept any password an older policy could have produced.
- 已将登录密码下限从 15 位降到 8 位，并用组成要求补足强度：密码现在必须至少包含大写字母、小写字母、数字、特殊符号四类中的两类。此前"15 位且无其他要求"是两头不讨好——长到足以逼用户复用密码或写在便利贴上，却仍然让 `aaaaaaaaaaaaaaa` 通过。字符按 Unicode general category 分类，因此非拉丁字符的密码适用同一条规则，不会仅因为不是 ASCII 就被拒。存量账户不受影响：登录与修改密码端点仍接受旧策略下可能产生的任何密码。
- Account details are now matched as substrings rather than whole values. The old rule only rejected a password that *equalled* the username or email; `alice2024` sailed through for user `alice`, which mattered little at fifteen characters and matters a great deal at eight. Fragments shorter than three characters are ignored, so the `a` of `a@example.com` does not block every honest password. The deny-list also gained the short common passwords that the lower minimum newly puts in reach (`password1`, `qwerty123`, `12345678`, and friends) — entries below the minimum length are unreachable, since the length check runs first.
- 账户信息现在按子串匹配，而不是整体相等。旧规则只拒绝与用户名或邮箱**完全相同**的密码，用户 `alice` 用 `alice2024` 可以直接通过；在 15 位下这影响有限，在 8 位下影响很大。长度小于 3 的片段会被忽略，因此 `a@example.com` 里的 `a` 不会挡住绝大多数正常密码。弱密码名单同时补入了因下限降低而重新变得可达的短常见密码（`password1`、`qwerty123`、`12345678` 等）——短于下限的条目不可达，因为长度检查先执行。
- Registration and password reset no longer disable their submit button. A greyed-out button cannot explain itself: the user is left comparing their password against a placeholder to guess which rule they missed. Both forms now validate on click, show the specific failing rule under each field, and focus the first field that needs work; a rule also appears early once the user leaves that field. Same for "Send code", which now says the email address is wrong instead of silently refusing to be pressed.
- 注册与重置密码页不再禁用提交按钮。变灰的按钮无法解释自己：用户只能对着 placeholder 猜自己漏了哪条要求。两个表单现在改为点击时校验，在对应字段下方显示具体未满足的那条规则，并把焦点移到第一个待修正的字段；用户离开某个字段后，该字段的问题也会提前提示。"发送验证码"按钮同理，现在会说明邮箱格式不对，而不是默默无法点击。
- Every password input gained a reveal toggle so a typo can be checked before submitting, and the password fields carry a line stating the composition requirement rather than only a length placeholder. Revealing is per field and always starts hidden, so an abandoned tab does not leave a plaintext password on screen.
- 所有密码输入框都增加了明文/密文切换按钮，便于提交前检查输入是否有误；密码框下方增加一行文字说明组成要求，而不再只有一个写着长度的 placeholder。明文切换按字段独立，且默认始终为密文，因此离开的页面不会把明文密码留在屏幕上。
- The encryption passphrase deliberately keeps the 15-character minimum. It is not a login password: it never reaches the server, it wraps the account key, and losing or guessing it costs the user every file they have encrypted, with no reset path. It now has its own named constant so the two limits can move independently.
- 加密 passphrase 有意保留 15 位下限。它不是登录密码：它从不发送到服务端，用于包装账户密钥，一旦遗失或被猜中，用户已加密的全部文件都将无法恢复，且没有重置路径。它现在使用独立命名的常量，两个下限可以各自调整。
- The browser now mirrors the policy in one shared module (`frontend/src/utils/password-policy.ts`) instead of a length constant copied into each page, so the form can name the exact failing rule while the user types. The server stays the authority and re-runs every rule; the common-password deny-list is deliberately not mirrored, so it can grow into a real breached-password corpus without shipping that corpus to every browser.
- 前端现在用一个共享模块（`frontend/src/utils/password-policy.ts`）镜像该策略，而不是把长度常量复制到每个页面，这样表单可以在用户输入时指出具体是哪条规则未满足。服务端仍是权威并会重新执行全部规则；弱密码名单有意不做镜像，以便日后扩充为真正的泄露密码库而无需下发到每个浏览器。

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
- Moved the changelog out of `CT_Logs/` into `changelog/`, and split it in two. `CT_Logs` was named for one track but had become the project's only change log, and nothing in the repository linked to it, so it was neither obviously shared nor easy to find. `changelog/CHANGELOG.md` is now the project-wide record every one of us writes to; per-work-package records moved to `changelog/work-packages/crypto-track.md`, keeping their text unchanged. `changelog/README.md` states which of the two a given entry belongs in, both READMEs link to the folder, and `AGENTS.md` carries the rule. `git log --follow` traces both files through the move.
- 已将更改日志从 `CT_Logs/` 迁至 `changelog/`，并拆分为两份。`CT_Logs` 以某一条线命名，实际上却成了项目唯一的更改日志，而仓库中没有任何位置链接到它——既看不出是共享的，也不容易找到。现在 `changelog/CHANGELOG.md` 是我们每个人共同书写的项目级记录；分工作包的记录迁至 `changelog/work-packages/crypto-track.md`，正文一字未改。`changelog/README.md` 写明了哪类条目该写进哪一份，两份 README 都已链接到该目录，`AGENTS.md` 中也加入了相应规则。两个文件都可以用 `git log --follow` 追溯到迁移之前。

### Scope note / 范围说明

- No application or cryptographic implementation code was changed in this update.
- 本次更新未修改应用程序代码或密码学实现代码。

update:2026/8/15 02:40
