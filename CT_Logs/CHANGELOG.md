# Changelog / 更新日志

All notable changes to this project are documented in this file.

本文件记录此项目的所有重要变更。

## [Unreleased] / [未发布]

### Deployment operations / 部署运维

- Distinguished a valid live audit chain (`LIVE_DATA`) from a fresh genesis state (`OK`) in
  the read-only MySQL deployment verifier. Live deployment still requires the singleton head
  to target the newest audit row with a matching hash and the exact Schema revision;
  `REVIEW`, `MISSING`, and `UNEXPECTED` continue to block releases. This fixes the false
  quarantine of frontend commit `acd0c9733eeb` without deleting audit evidence or bypassing
  the database gate.
- 在 MySQL 只读部署核验中区分有效在线审计链（`LIVE_DATA`）与全新初始状态（`OK`）。在线
  部署仍要求单例链头指向最新审计记录、哈希一致并保留准确的 Schema revision；
  `REVIEW`、`MISSING` 与 `UNEXPECTED` 仍会阻止发布。该修复解除前端提交
  `acd0c9733eeb` 的误隔离，不会删除审计证据，也不会绕过数据库门禁。
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

update:2026/8/12 14:48

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

-------------------------------------------------------------------------------------------------------------
## CT-1.2

Base `main` @ `c45e54d` · Scope: file encryption only · No backend changes
基线 `main` @ `c45e54d` · 范围：仅文件加密 · 未改动后端

### Added / 新增

- `frontend/src/crypto/encoding.ts` — byte encoding: integers, UUIDs, NFC-normalized UTF-8,
  canonical Base64, length prefixes.
- `frontend/src/crypto/encoding.ts` — 字节编码：整数、UUID、NFC 归一化 UTF-8、规范 Base64、
  长度前缀。
- `frontend/src/crypto/primitives.ts` — AES-256-GCM (detached tag), SHA-256,
  RSA-OAEP-SHA256, RSA-PSS-SHA256.
- `frontend/src/crypto/primitives.ts` — AES-256-GCM（分离 tag）、SHA-256、RSA-OAEP-SHA256、
  RSA-PSS-SHA256。
- `docs/crypto/test_vectors.json` and 41 vitest cases. Vectors are generated with
  `python-cryptography`, so the TypeScript is checked against an independent implementation
  rather than against itself.
- `docs/crypto/test_vectors.json` 与 41 项 vitest 用例。向量由 `python-cryptography` 生成，
  使 TypeScript 对照独立实现验证，而非自我往返验证。
- `vitest` declared in `package.json` with `package-lock.json` synchronized.
- 已在 `package.json` 声明 `vitest`，并同步 `package-lock.json`。

### Why / 用途

The frontend had no encryption at all; uploads sent plaintext. These are the primitives every
encrypted upload needs: ciphertext, nonce, tag, and RSA-wrapped keys.
前端此前没有任何加密，上传发送的是明文。这些是每次加密上传都需要的底层原语：密文、nonce、
tag 与 RSA 包装的密钥。

Three rules the backend already enforces are now caught by tests instead of at runtime:
三条后端已在强制、但此前无人知晓的规则，现在由测试拦截，而不是等到运行时才发现：

- The GCM tag must be detached from the ciphertext, or the upload is rejected.
- GCM tag 必须与密文分离，否则上传被拒。
- Base64 must be standard and padded, or the request is rejected.
- Base64 必须是标准字母表且带填充，否则请求被拒。
- Filenames must be NFC-normalized, or upload succeeds and later decryption fails.
- 文件名必须 NFC 归一化，否则上传成功、之后解密失败。

### Not included / 未包含

- Argon2id and the account-key envelopes, while the key-custody model is unresolved on `main`.
- Argon2id 与账户密钥信封 —— `main` 上的密钥托管模型尚未定论。
- File envelope assembly and AAD construction, which follow in the next step.
- 文件信封组装与 AAD 构造，将在下一步完成。

### Notes / 说明

- The existing `file_api.upload` is broken independently of this work: it posts the plaintext
  file to `/files/upload`, while the backend serves `POST /files` and requires ciphertext plus
  a metadata envelope.
- 现有 `file_api.upload` 本身即为损坏状态，与本次工作无关：它把明文文件发往 `/files/upload`，
  而后端提供的是 `POST /files`，且要求密文加元数据信封。
- `vue-tsc` cannot run here; it has drifted from the installed `typescript`. Used
  `tsc --noEmit` instead. Pre-existing.
- `vue-tsc` 在此无法运行，与已安装的 `typescript` 版本漂移。改用 `tsc --noEmit`。该问题早于
  本分支存在。

update: 2026/8/20
