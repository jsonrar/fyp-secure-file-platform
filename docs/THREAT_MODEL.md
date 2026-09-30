# Threat Model

English | [简体中文](THREAT_MODEL.zh-CN.md)

| | |
|---|---|
| Version | 0.3 — accuracy corrections from peer review of v0.1; owner-key substitution added |
| Tracks | [Issue #60](https://github.com/jsonrar/fyp-secure-file-platform/issues/60) |
| Status | **Self-assessment.** Written by the crypto & security lead, who also implemented much of the cryptography it assesses. It is not an independent review and certifies nothing. |
| Reflects | `main` at the time of writing, schema revision `0008_avatars`, staging at `https://secureview.tech` |

This document states what SecureView protects, from whom, where the trust boundaries lie, and
which threats each boundary does and does not stop. It consolidates controls that are
specified in detail elsewhere rather than restating them; each row links to the document or
code that is the source of truth. Where a control is claimed, the claim was checked against
the code or the live deployment, not assumed.

**Reading the status column.** *Mitigated* means a control exists and was verified.
*Partial* means a control exists but leaves a named gap. *Accepted* means the risk is known and
deliberately carried at FYP scope. *Open* means it is a finding to be resolved.

**Implemented is not deployed.** A control that exists in the repository but whose operation on
staging has not been verified is never marked *Mitigated*; the row says which half is missing.
The staging evidence tables in
[OBSERVABILITY § 8](OBSERVABILITY_AND_INCIDENT_RESPONSE.md#8-staging-evidence-record) and
[BACKUP_AND_RECOVERY](BACKUP_AND_RECOVERY.md#staging-installation-record-2026-09-24) are the
record this document checks against.

---

## 1. System in one paragraph

A Vue single-page app in the browser performs all file and account-key cryptography. It
encrypts each file under a fresh data encryption key (DEK), wraps that DEK to the owner's RSA
public key and to an offline recovery public key, and uploads only ciphertext. The account
private key is sealed in the browser under a key derived from an encryption passphrase that
never leaves the browser. A FastAPI backend behind nginx authenticates sessions, stores
ciphertext on local disk and envelopes in MySQL 8.4, enforces sharing and recovery policy, and
appends every security-sensitive change to a hash-chained audit log. Everything runs on one
VPS. See [ARCHITECTURE.md](ARCHITECTURE.md) and [SECURITY_FLOWS.md](SECURITY_FLOWS.md).

## 2. Security objectives

| # | Objective |
|---|---|
| O1 | Under the trusted client-code and API-boundary model, the backend, database and storage never hold the plaintext material needed to read file contents or unwrap a DEK — so compromising or stealing them yields no plaintext. This does **not** extend to an operator who replaces the client code (N1). |
| O2 | A file's content and the metadata bound into its AAD cannot be altered undetected. |
| O3 | Only the owner, current grantees, and an approved recovery can obtain a file's key. |
| O4 | A stolen server-side session alone cannot read files or seize the account's key custody. |
| O5 | Security-relevant actions are recorded in a log whose silent rewriting is detectable. |
| O6 | A forgotten *login password* is recoverable; a forgotten *encryption passphrase* is recoverable only by whoever holds the account's private key file. |

## 3. Explicit non-goals

These are out of scope by design. Stating them is part of the model: a reviewer should not
credit the system with protections it does not claim.

| # | Non-goal | Why |
|---|---|---|
| N1 | Protection from an **actively malicious server** that serves substituted code, keys, or ciphertext. | The browser runs JavaScript the server delivers. A server willing to ship hostile code can exfiltrate the passphrase. Zero-knowledge holds at the **API boundary**, not against the code supplier. See [SECURITY_FLOWS.md § Metadata Leakage](SECURITY_FLOWS.md#metadata-leakage-and-threat-limits). |
| N2 | Confidentiality of **file metadata**: filename, MIME type, size, timestamps, ownership, sharing graph. | Stored in cleartext columns so the server can list, search and enforce policy. Filename, MIME type and plaintext size are bound into AAD-3, so altering them is detected at decryption; timestamps, ownership and the sharing graph are cleartext, server-controlled, and not covered by any file tag. Revisited in step 3. |
| N3 | Anonymity and resistance to **traffic analysis**. | Access timing, IP addresses and ciphertext sizes are visible to the server and the network. |
| N4 | Protection of a **compromised endpoint**: malware, a malicious browser extension, or someone at the unlocked keyboard. | Whatever can read the page can read what the user decrypts. |
| N5 | **Retracting** plaintext or keys a recipient already obtained. | Revocation stops future server-mediated access; it cannot erase a download or a DEK already unwrapped. |
| N6 | Recovering a forgotten encryption passphrase **without** the private key file. | The server holds nothing that opens the AMK envelope. This is the price of O1. |
| N7 | High availability, geographic redundancy, and certification against any standard. | FYP scope, one VPS. |

## 4. Assets

| ID | Asset | Where it exists | Impact if disclosed | Impact if altered or lost |
|---|---|---|---|---|
| A1 | File plaintext | User's browser memory only, transiently | Total loss of confidentiality for that file | — |
| A2 | File DEK | Browser memory; stored only RSA-wrapped (`file_key_wrappings`) | Opens that one file | File unrecoverable |
| A3 | Encryption passphrase | User's head; browser memory during unlock | With the database, opens the account private key | O6 limits apply |
| A4 | Account master key (AMK) | Browser memory during unlock; stored only wrapped under the KEK | Opens the private-key bundle | Account locked out |
| A4a | Key-encryption key (KEK) | Derived from the passphrase with Argon2id each unlock; browser memory only; **never persisted** | Opens the stored wrapped AMK | Nothing to lose: re-derived from the passphrase |
| A5 | Account private key (RSA-3072) | Plaintext PEM exported once at registration; sealed bundle in DB; non-extractable `CryptoKey` while unlocked | Opens every file wrapped to the account | Files wrapped only to it are lost |
| A6 | Recovery private key | **Intended:** offline, per the *proposed* custody in [BACKUP_AND_RECOVERY.md § 7](BACKUP_AND_RECOVERY.md#7-recovery-key-custody). **Staging today:** an unencrypted PEM on a team member's workstation (T-I8) | Opens **every** file's recovery wrapping | Recovery impossible for files wrapped to it |
| A7 | Login password | User's head; Argon2id hash in DB | Account takeover of the server-side session | Resettable by email (O6) |
| A8 | Access and refresh tokens | Browser `localStorage`; SHA-256 hashes in DB | Session takeover until expiry or revocation | Re-login |
| A9 | Ciphertext objects | VPS disk, mode-0700 directory owned by the service user; encrypted backups | Nothing without A2 | Integrity failure; restore from backup |
| A10 | File metadata and sharing graph | MySQL cleartext columns | Privacy loss (N2) | Detected at decryption for AAD-bound fields; not for the rest |
| A11 | Audit log and chain head | MySQL. HMAC-authenticated external checkpoints are implemented; their staging operation is not yet verified (T-T6) | Reveals activity | Tampering must be detectable (O5) |
| A12 | Server secrets: `SECRET_KEY`, DB credentials, email API key, audit-checkpoint HMAC key | VPS protected environment and root-only files | Forged verification codes, DB access, mail abuse, forged checkpoints | Outage |
| A13 | Backup private key | Intended: offline, under the same proposed custody as A6. Its current location is not recorded in the staging installation record | Opens every backup set | Backups unreadable |
| A14 | Deployed code | GitHub `main`, pulled to the VPS by a read-only deploy key | See N1: whoever controls it controls A3 | — |

## 5. Actors and adversaries

| ID | Actor | Legitimate capability | Must not be able to |
|---|---|---|---|
| U1 | Anonymous internet user | Register, request a verification code, log in | Brute-force logins, reach any file, enumerate accounts (only partly prevented — T-S2) |
| U2 | Authenticated USER | Upload, download, share and revoke own files; request recovery for own key | Read others' files or metadata; escalate role |
| U3 | Share recipient | Decrypt files shared to them while the grant is live | Re-share without `can_share`; keep server-mediated access after revocation |
| U4 | RECOVERY_OFFICER | Approve or reject recovery requests; run offline rewrap | Approve their own request; obtain a file DEK online; read plaintext |
| U5 | ADMIN | Register recovery keys, verify the audit chain, manage roles | Read file contents or users' private keys |
| X1 | Network attacker | Observe and modify traffic between browser and nginx | Read or alter anything under TLS (HSTS, `includeSubDomains`) |
| X2 | Holder of a stolen session token | Act as the user against the API until revoked | Read files (needs A3 or A5); replace key envelopes (needs A5 — see T-E3) |
| X3 | Database or disk thief (dump, backup leak, disk image) | Read every row and object | Read files (O1); only offline passphrase guessing against A3 remains |
| X4 | Malicious or compromised server operator | Everything X3 can, plus modify stored data and **the code served to browsers** | Covered only up to N1 |
| X5 | Supply-chain attacker | Publish a malicious version of a dependency or push to `main` | See T-T5 and T-E5 |
| X6 | Insider on the team with repository write access | Merge to `main`, which auto-deploys | Bypass review (currently possible — T-E5) |
| X7 | Malicious recipient | Everything U3 can | Anything beyond N5 |

## 6. Trust boundaries

```text
            TB1 (TLS)              TB2 (loopback)          TB3 (TLS, required)
[Browser] ────────────> [nginx] ──────────────> [FastAPI] ─────────────────> [MySQL 8.4]
   │  TB0: plaintext,               │                │ TB4 (fs, 0700)
   │  keys, passphrase stay here    │                └───────────────> [ciphertext on disk]
   │                                │                │ TB5 (HTTPS)
   │                                │                └───────────────> [email provider]
   │                         TB6: GitHub main ── read-only deploy key ──> [VPS release]
   │                         TB7: backups and audit checkpoints ──> [off-server storage]
   └── TB8: recovery and backup private keys — intended offline; see A6 for staging today
```

| ID | Boundary | What crosses it | Principal control |
|---|---|---|---|
| TB0 | Inside the browser vs. everything else | **Stays client-side:** file plaintext, the encryption passphrase, AMK, KEK, plaintext private keys and DEKs. **Crosses to the API:** ciphertext, wrapped keys, public keys and signatures, and also login passwords, verification codes, bearer and refresh tokens, usernames and emails, and cleartext metadata — filenames, MIME types, sizes | All secret-bearing *cryptography* is client-side; authentication secrets do cross, under TLS. [SECURITY_FLOWS.md](SECURITY_FLOWS.md) |
| TB1 | Browser ↔ nginx | Everything the API carries | TLS; HSTS one year with `includeSubDomains`; port 80 redirects with 308 |
| TB2 | nginx ↔ FastAPI | Proxied requests | Configured to bind `127.0.0.1:8000` with trusted proxy `forwarded-allow-ips=127.0.0.1`; the live bind check is still pending in OBSERVABILITY § 8 |
| TB3 | FastAPI ↔ MySQL | Envelopes, metadata, audit rows | `require_secure_transport=1`; least-privilege runtime account with no DDL |
| TB4 | FastAPI ↔ object storage | Ciphertext | Service user owns a mode-0700 root; SHA-256 recorded at upload and checked at download |
| TB5 | FastAPI ↔ email provider | Verification codes to user addresses | HTTPS API; codes stored only as HMAC digests |
| TB6 | GitHub ↔ VPS | Release code | Read-only deploy key; release gate with database verification and quarantine |
| TB7 | VPS ↔ off-server storage | Encrypted backups, HMAC checkpoints | Backup host holds only a public key (installed and running on staging). A 30-day bucket lock is part of the design, but the staging installation record does not verify it. Checkpoints are not yet uploaded from staging |
| TB8 | Networked systems ↔ offline custody | Recovery and backup private keys | Procedural only, and not yet in effect on staging (A6). What *is* enforced in code: no endpoint accepts a recovery private key |

## 7. STRIDE analysis

Each threat has a stable ID for later steps and for the findings register (step 4).

### 7.1 Spoofing

| ID | Threat | Control | Status |
|---|---|---|---|
| T-S1 | Password guessing against login | Argon2id hashes; per-account and per-IP throttles in `auth_login_throttles`; nginx `secureview_auth` at 12 requests per minute per IP | Mitigated |
| T-S2 | Account enumeration through registration, code sending or password reset | Code sending and password reset answer identically whether or not the account exists, and spend the allowance either way | Partial — `POST /auth/register` answers `409 account_identifier_unavailable` for a taken username **or** email, and checks this *before* the verification code, so existence can be probed without a valid code. Bounded only by the per-IP registration throttle. Step 4. |
| T-S3 | Session hijack by token theft | Tokens stored only as SHA-256; access 30 min, refresh 7 days, absolute 7 days; a replayed refresh token revokes the whole session family (`AUTH_REFRESH_REPLAY_DETECTED`) | Partial — see T-I4 for where tokens are kept |
| T-S4 | Substituted **recovery public key**, so every future upload is wrapped to an attacker | Browser recomputes the fingerprint from the PEM and displays it; the API's own fingerprint field is never trusted | Partial — nothing pins it; the user must compare out of band. Step 3. |
| T-S5 | Substituted **recipient public key** during sharing | Recipient resolved by exact username or email; the browser wraps the DEK to whatever `public_key_pem` the API returns | Open — the sharing flow neither recomputes, shows, pins nor asks the sender to confirm the recipient's fingerprint. Step 3. |
| T-S6 | Forged emailed verification code | 10-minute TTL, attempt limit, HMAC digest keyed by `SECRET_KEY`, purpose and address | Mitigated |
| T-S7 | Substituted **owner public key** during upload, so the owner's own wrapping goes to an attacker | The browser takes the owner key from `GET /keys/me` and wraps the DEK to it | Open — like T-S4 and T-S5, nothing pins the owner's own key. Step 3 treats all three as one public-key identity problem. |

### 7.2 Tampering

| ID | Threat | Control | Status |
|---|---|---|---|
| T-T1 | Altering ciphertext at rest or in transit | AEAD tag; the server also verifies SHA-256 before serving | Mitigated |
| T-T2 | Relabelling a file's name, MIME type, size or algorithm | All bound into AAD-3; any change fails authentication ([FILE_ENVELOPE.md](crypto/FILE_ENVELOPE.md)) | Mitigated |
| T-T3 | Replacing a user's key envelopes with garbage to lock them out | Rewrap, key addition and passphrase reset all require an RSA-PSS signature by the account private key, each under its own domain label | Mitigated |
| T-T4 | **Rolling back** a key bundle, protection profile or file to an earlier valid version | Optimistic revisions stop concurrent writers, but the client does not pin what it last saw | Open — a malicious server can serve an older valid state. Step 3. |
| T-T5 | Malicious dependency version | Lockfiles; `@noble/ciphers` chosen for zero transitive dependencies | Partial — no provenance or audit gate. Step 4. |
| T-T6 | Rewriting the audit log consistently | Hash chain in the database; external HMAC-authenticated chain-head checkpoints implemented in `backend/scripts/audit_checkpoint.py`, with the HMAC key never given to the backend | Partial — the hash chain is live. The external checkpoints exist in the repository, but the first staging upload and its off-host verification are still pending, so no external trust anchor is in operation yet. |
| T-T7 | Tampering with an execution package during offline recovery | Server rechecks identities, lengths and the live grant before accepting the rewrap | Partial — the offline workstation is procedural (TB8) |

### 7.3 Repudiation

| ID | Threat | Control | Status |
|---|---|---|---|
| T-R1 | A user denies having shared, requested a download of, or reset | Every such action appends an audit event with actor, target, IP and user agent in the same transaction | Mitigated for what is recorded. A download is recorded as `FILE_DOWNLOAD_AUTHORIZED` when the server authorizes the request and has verified the ciphertext, **before** streaming it. That is evidence of an authorized request, not proof that the client received the whole stream or decrypted it. |
| T-R2 | An operator denies altering records | External HMAC checkpoints (T-T6), once operating | Partial — not yet operating on staging, and even then they cover the chain head, not who ran what on the host |
| T-R3 | A recovery officer denies approving or executing | Approval and execution are separate audited events; a requester cannot review their own request | Partial — one officer may both approve and execute ([SECURITY_FLOWS.md § Offline Recovery](SECURITY_FLOWS.md#offline-recovery-boundary)) |

### 7.4 Information disclosure

| ID | Threat | Control | Status |
|---|---|---|---|
| T-I1 | Database or disk theft exposes file contents | Nothing on the server opens a DEK (O1) | Mitigated |
| T-I2 | Database theft enables **offline passphrase guessing** | Argon2id at 64 MiB and 3 iterations; minimum 10 characters | Partial — measured in [§9](#9-argon2id-cost-and-the-passphrase-minimum): the KDF cost is adequate, but the length-only check admits passphrases that fall in minutes. |
| T-I3 | Metadata leakage: filenames, sizes, sharing graph | None beyond access control | Accepted (N2); the encrypted-manifest decision is step 3 |
| T-I4 | **XSS steals tokens** from `localStorage` | CSP `script-src 'self' 'wasm-unsafe-eval'`, `object-src 'none'`, `frame-ancestors 'none'`. Vue escapes interpolation; the only two `v-html` sinks render bundled content — the logo SVG and the static knowledge-base articles, which `render-knowledge-content.ts` escapes before formatting — so no user- or server-supplied string reaches them today. | Partial — any future XSS reads both tokens. It still cannot extract the private key: it is held as a non-extractable `CryptoKey` and relocks after 15 idle minutes. It *can* use the key to decrypt while it is unlocked. |
| T-I5 | Secrets in logs | Documented exclusion list; `repr=False` on secret fields; [OBSERVABILITY § 7](OBSERVABILITY_AND_INCIDENT_RESPONSE.md#7-verification-that-sensitive-data-stays-out) | Partial — controls are in code; the live check that redaction markers are absent from staging outputs is still pending in OBSERVABILITY § 8 |
| T-I6 | **Public API documentation on staging** | `/docs`, `/redoc` and `/openapi.json` answer `200` on `https://secureview.tech`, and those locations use a relaxed CSP that loads script from `cdn.jsdelivr.net` | Open — low severity. Recorded in step 4. |
| T-I7 | The plaintext PEM export is mishandled by the user | Shown once with a warning; read locally and never uploaded when used | Accepted — custody decision in step 3 |
| T-I8 | Recovery private key exposure | Custody procedure in [BACKUP_AND_RECOVERY.md § 7](BACKUP_AND_RECOVERY.md#7-recovery-key-custody) | Open — the procedure is marked *proposed*, and the current staging recovery key is held as an unencrypted PEM on a team member's workstation, not offline. Step 3. |
| T-I9 | A share recipient keeps what they downloaded | — | Accepted (N5) |

### 7.5 Denial of service

| ID | Threat | Control | Status |
|---|---|---|---|
| T-D1 | Request flooding | nginx `secureview_api` at 10 requests per second per IP, burst 20 | Partial — per-IP only |
| T-D2 | Upload abuse filling the disk | 500 MiB per upload in nginx and backend; per-user quota not enforced | Open — step 4 |
| T-D3 | Very large uploads exhaust the **browser** | — | Accepted — the in-memory design peaks near four times the file size; owned by the upload work, not this model |
| T-D4 | Lock-out by envelope overwrite | See T-T3 | Mitigated |

### 7.6 Elevation of privilege

| ID | Threat | Control | Status |
|---|---|---|---|
| T-E1 | A USER reaches ADMIN or RECOVERY_OFFICER routes | Admin and recovery routes depend on the role guards in `app/api/dependencies.py` (ADMIN, or ADMIN/RECOVERY_OFFICER) | Mitigated |
| T-E2 | A recipient re-shares without permission | `can_share` checked server-side | Mitigated |
| T-E3 | A stolen session seizes key custody (e.g. resets the passphrase) | Reset requires a signature by the private key, not a session | Mitigated |
| T-E4 | A requester self-approves recovery | Requester ≠ reviewer enforced by a database CHECK | Mitigated |
| T-E5 | Code reaches production without review | CI runs on every pull request and on every push to `main` | Open — `main` has **no branch protection**, so a direct push bypasses PR review. CI still runs on it, but the server-pull deployment neither waits for CI nor requires it to pass before deploying that commit. Step 4. |
| T-E6 | Running application reaches the host | Unprivileged `fypapp` service user; loopback-only binding | Partial — no container or systemd sandboxing is claimed here |

## 8. Abuse cases

Worked end-to-end, each names the threats it chains.

1. **Stolen laptop session.** X2 opens the site with a live token. They can list files and
   metadata (T-I3) but cannot decrypt without the passphrase or key file, and cannot reset the
   passphrase without the key file (T-E3). *Residual:* metadata exposure until the session
   expires or is revoked.
2. **Leaked database dump.** X3 has every envelope. Files are safe (T-I1). The attacker runs an
   offline dictionary against each account's Argon2id envelope (T-I2). *Residual:* weak
   passphrases fall; strong ones do not. §9 quantifies both: a leaked-list passphrase falls in
   under two days on one laptop, four random words survive a million of them for about two years.
3. **Swapped recovery key.** X4 registers its own recovery public key. Every later upload
   wraps its DEK to X4 (T-S4). The upload page shows a different fingerprint, but only a user
   who compares it out of band notices. *Residual:* high impact, detection depends on the user.
4. **XSS in a future feature.** A script injection bypasses Vue escaping. It reads both tokens
   (T-I4) and, if the key is unlocked, decrypts whatever it asks for. It cannot export the
   private key. *Residual:* depends on the CSP holding.
5. **Unreviewed push.** A collaborator's machine is compromised and pushes to `main` (T-E5).
   Auto-deploy ships it; the code can capture passphrases (N1). *Residual:* the whole model
   rests on `main` being trustworthy.
6. **Revoked recipient.** X7 downloaded a file before revocation. They keep it (T-I9, N5).
   Revocation works as designed and cannot do more.

## 9. Argon2id cost and the passphrase minimum

Issue #60 criterion 2. The question is whether the enrolled KDF cost and the 10-character
passphrase minimum together make threat T-I2 — offline guessing after database theft —
acceptable, and what a user pays for it at unlock.

### 9.1 Method

- **Defender side.** `/benchmark/argon2` runs the production `deriveKek` — the same function,
  hash-wasm 4.12.0 build and parameters the unlock dialog uses — once untimed to warm up
  WebAssembly, then five timed runs per configuration with a fresh random salt each time. Run
  on a local production build (`vite preview`), which executes the same bundle as staging.
- **Attacker side.** `backend/scripts/benchmark_argon2_offline.py` runs argon2-cffi, the native
  C reference implementation, at the same parameters on one core and then on every core.
- **Same function.** The `argon2id_kek` vectors in
  [`test_vectors.json`](crypto/test_vectors.json) are generated by argon2-cffi and reproduced byte
  for byte by the browser's `deriveKek`, so the attacker figures apply to real envelopes rather
  than to a lookalike.
- **Raw data** is kept in [`benchmarks/argon2id-2026-09-30.json`](benchmarks/argon2id-2026-09-30.json).

### 9.2 What an unlock costs the user

Median of five runs, 2026-09-30.

| Cost | Chrome 153, macOS | Safari 18.6, macOS | iOS 26.6 (Quark, WebKit) |
|---|---|---|---|
| **64 MiB, t=3 (production)** | **100 ms** | **106 ms** | **151 ms** |
| 64 MiB, t=6 | 195 ms | 205 ms | 269 ms |
| 128 MiB, t=3 | 206 ms | 1 327 ms ⚠ | 268 ms |
| 256 MiB, t=3 | 426 ms | 433 ms | 555 ms |

The production cost is **0.10–0.15 s** on every client tested, and an unlock happens once per page
load — the opened key lives only in page memory — and again after each 15-minute idle relock. The user-facing cost of the current
setting is negligible.

Notes on the data, stated rather than smoothed:

- **Coverage is thin.** Two desktop engines on one Apple Silicon Mac and one iPhone. **No Android
  device, no Firefox, and no low-end or older hardware were measured**, and those are where
  Argon2id is slowest. The project has never declared which clients it supports, so "supported
  clients" is defined here as the tested set, and the gap is carried to the findings register.
- **Safari at 128 MiB is anomalous.** It took 1.3 s in all five runs, six times slower than the
  same browser at 256 MiB. It is not explained. It does not affect the production cost, but it
  must be reproduced before any change to 128 MiB.
- Every iOS browser is WebKit, so the Quark result approximates iOS Safari. The macOS user-agent
  strings say "Intel" because browsers freeze that string; the machine is Apple Silicon.

### 9.3 The parameters against published guidance

- **RFC 9106 §4, second recommended option:** Argon2id, t=3, p=4, m=64 MiB, 128-bit salt, 256-bit
  tag. SecureView matches it — 16-byte salt, 32-byte output — except for p=1. hash-wasm computes lanes one after another on a single thread, so four lanes
  would cost the defender the same wall time for the same memory and passes. p=1 is the honest
  setting for this implementation.
- **OWASP Password Storage Cheat Sheet minimum:** m=19 MiB, t=2, p=1. Exceeded.
- **The server's bounds** (`KeyProtectionProfileIn`) accept 64 MiB–1 GiB, 1–10 iterations and 1–16
  lanes, so raising the cost needs no backend change.

### 9.4 What guessing costs an attacker

One 10-core Apple Silicon laptop runs **52.8–58.3 guesses per second** across all cores, and 11
per second on one core. Ten cores buy only a 5.3× speedup because each guess occupies 64 MiB and
memory bandwidth, not core count, is the limit. The table uses **60 per second**, rounded in the
attacker's favour.

The multipliers are assumptions, not measurements. This document makes no claim about GPU or
ASIC throughput against Argon2id. A larger multiplier shortens every row proportionally.

Each account has its own salt, so every figure is **per account**.

| Passphrase | 1 laptop | 1 000 × | 1 000 000 × |
|---|---|---|---|
| In the first 10 000 of any guessing list (`aaaaaaaaaa`, `password12`, `qwertyuiop`) | 2.8 minutes | 0.2 s | instant |
| Anywhere in a 10-million-entry leaked-password list | 1.9 days | 2.8 minutes | 0.2 s |
| 10 random lowercase letters (26¹⁰) | 74 600 years | 75 years | 27 days |
| 4 random Diceware words (7776⁴, ≈51.7 bits) | 1.9 million years | 1 930 years | 1.9 years |
| 10 random printable ASCII characters (94¹⁰) | 2.8 × 10¹⁰ years | 2.8 × 10⁷ years | 28 400 years |

Times are to exhaust the whole space; the expected time to success is half.

### 9.5 Verdict

1. **The KDF cost is not the weak link.** At the current setting, any passphrase with about 50
   bits of real entropy — four random words — withstands a million laptops for years, and costs
   its owner a tenth of a second to unlock.
2. **The 10-character minimum is a usability floor, not a strength guarantee.** The check is
   length-only, plus "differs from the login password". `aaaaaaaaaa` and `password12` pass it,
   and fall in minutes on one laptop. Length is a poor proxy for entropy when people choose.
3. **Only the browser can do better.** The passphrase never reaches the server, by design (O1),
   so the server can neither check it against a deny-list nor enforce anything about it. Any
   strength check must run client-side.

This leads to two recommendations for the findings register (step 4):

- **R-1 (the one that matters): reject known-weak passphrases in the browser.** Apply the login
  password's deny-list, reject repeated and sequential patterns and the account's own
  identifiers, and steer users toward four or more random words. This closes the gap between
  rows 1–2 and rows 4–5 of the table far more than any cost increase could.
- **R-2 (optional): raise the enrolled cost.** There is measured headroom: 256 MiB, t=3 is at most
  0.56 s on every tested client and quadruples an attacker's cost per guess. Cost is stored per
  profile, so new enrolments would take the new value and existing accounts would upgrade at
  their next passphrase change or reset. **Do not change it until** a low-end Android device has
  been measured and the Safari 128 MiB anomaly reproduced.

## 10. Planned sections

Filled in by the next steps of Issue #60.

| Step | Section | Issue #60 criterion |
|---|---|---|
| 3 | PEM export custody and lost-passphrase limits; rollback; owner-, recipient- and recovery-key substitution (T-S4, T-S5, T-S7) with fingerprint and revision pinning and an independent trust anchor; encrypted-manifest decision and residual metadata leakage | 3, 4, 5 |
| 4 | Dependency and supply-chain policy, CSP exceptions, upload abuse, token storage, offline recovery operations; findings register with severity, disposition and evidence | 6, 7 |

## 11. Revision history

| Version | Change |
|---|---|
| 0.1 | Objectives, non-goals, assets, actors, trust boundaries, STRIDE analysis, abuse cases. |
| 0.2 | §9: Argon2id measured on three clients and against a native attacker; verdict on the 10-character minimum; recommendations R-1 and R-2. |
| 0.3 | Peer-review corrections: O1 scoped to trusted client code; TB0 lists everything that actually crosses; N2 and AAD scope; AMK and KEK separated; recipient fingerprint is **not** shown (T-S5); CI does run on pushes to `main` but deployment does not wait for it (T-E5); download audit proves authorization, not receipt (T-R1); recovery-key custody split into intended vs staging; external checkpoints, bucket lock, loopback bind and log redaction marked implemented-but-unverified; owner-key substitution added as T-S7. |
