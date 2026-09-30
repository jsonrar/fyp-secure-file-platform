# Threat Model

English | [简体中文](THREAT_MODEL.zh-CN.md)

| | |
|---|---|
| Version | 0.1 — actors, assets, boundaries, non-goals, and STRIDE analysis |
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
| O1 | The server, its operator, and anyone who steals its database or disk cannot read file contents or unwrap any file key. |
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
| N2 | Confidentiality of **file metadata**: filename, MIME type, size, timestamps, ownership, sharing graph. | Stored in cleartext columns so the server can list, search and enforce policy. Bound into the AAD, so it cannot be *altered*, but it is readable. Revisited in step 3. |
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
| A4 | Account master key (AMK) and KEK | Browser memory during unlock; stored only wrapped | Opens the private-key bundle | Account locked out |
| A5 | Account private key (RSA-3072) | Plaintext PEM exported once at registration; sealed bundle in DB; non-extractable `CryptoKey` while unlocked | Opens every file wrapped to the account | Files wrapped only to it are lost |
| A6 | Recovery private key | Offline, per [BACKUP_AND_RECOVERY.md § 7](BACKUP_AND_RECOVERY.md#7-recovery-key-custody) | Opens **every** file's recovery wrapping | Recovery impossible for files wrapped to it |
| A7 | Login password | User's head; Argon2id hash in DB | Account takeover of the server-side session | Resettable by email (O6) |
| A8 | Access and refresh tokens | Browser `localStorage`; SHA-256 hashes in DB | Session takeover until expiry or revocation | Re-login |
| A9 | Ciphertext objects | VPS disk, mode-0700 directory owned by the service user; encrypted backups | Nothing without A2 | Integrity failure; restore from backup |
| A10 | File metadata and sharing graph | MySQL cleartext columns | Privacy loss (N2) | Detected at decryption for AAD-bound fields; not for the rest |
| A11 | Audit log and chain head | MySQL; HMAC checkpoints in object-locked storage | Reveals activity | Tampering must be detectable (O5) |
| A12 | Server secrets: `SECRET_KEY`, DB credentials, email API key, audit-checkpoint HMAC key | VPS protected environment and root-only files | Forged verification codes, DB access, mail abuse, forged checkpoints | Outage |
| A13 | Backup private key | Offline, like A6 | Opens every backup set | Backups unreadable |
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
   │                         TB7: backups and audit checkpoints ──> [object-locked storage]
   └── TB8: offline recovery and backup private keys, never on a networked host (by policy)
```

| ID | Boundary | What crosses it | Principal control |
|---|---|---|---|
| TB0 | Inside the browser vs. everything else | Only ciphertext, wrapped keys, public keys, signatures | All secret-bearing cryptography is client-side; [SECURITY_FLOWS.md](SECURITY_FLOWS.md) |
| TB1 | Browser ↔ nginx | Everything the API carries | TLS; HSTS one year with `includeSubDomains`; port 80 redirects with 308 |
| TB2 | nginx ↔ FastAPI | Proxied requests | Backend binds `127.0.0.1:8000`; trusted-proxy `forwarded-allow-ips=127.0.0.1` |
| TB3 | FastAPI ↔ MySQL | Envelopes, metadata, audit rows | `require_secure_transport=1`; least-privilege runtime account with no DDL |
| TB4 | FastAPI ↔ object storage | Ciphertext | Service user owns a mode-0700 root; SHA-256 recorded at upload and checked at download |
| TB5 | FastAPI ↔ email provider | Verification codes to user addresses | HTTPS API; codes stored only as HMAC digests |
| TB6 | GitHub ↔ VPS | Release code | Read-only deploy key; release gate with database verification and quarantine |
| TB7 | VPS ↔ off-server storage | Encrypted backups, HMAC checkpoints | Backup host holds only a public key; object lock on the bucket |
| TB8 | Networked systems ↔ offline custody | Recovery and backup private keys | Procedural only: no endpoint accepts a recovery private key |

## 7. STRIDE analysis

Each threat has a stable ID for later steps and for the findings register (step 4).

### 7.1 Spoofing

| ID | Threat | Control | Status |
|---|---|---|---|
| T-S1 | Password guessing against login | Argon2id hashes; per-account and per-IP throttles in `auth_login_throttles`; nginx `secureview_auth` at 12 requests per minute per IP | Mitigated |
| T-S2 | Account enumeration through registration, code sending or password reset | Code sending and password reset answer identically whether or not the account exists, and spend the allowance either way | Partial — `POST /auth/register` answers `409 account_identifier_unavailable` for a taken username **or** email, and checks this *before* the verification code, so existence can be probed without a valid code. Bounded only by the per-IP registration throttle. Step 4. |
| T-S3 | Session hijack by token theft | Tokens stored only as SHA-256; access 30 min, refresh 7 days, absolute 7 days; a replayed refresh token revokes the whole session family (`AUTH_REFRESH_REPLAY_DETECTED`) | Partial — see T-I4 for where tokens are kept |
| T-S4 | Substituted **recovery public key**, so every future upload is wrapped to an attacker | Browser recomputes the fingerprint from the PEM and displays it; the API's own fingerprint field is never trusted | Partial — nothing pins it; the user must compare out of band. Step 3. |
| T-S5 | Substituted **recipient public key** during sharing | Recipient resolved by exact username or email; fingerprint shown | Partial — no pinning or verification ceremony. Step 3. |
| T-S6 | Forged emailed verification code | 10-minute TTL, attempt limit, HMAC digest keyed by `SECRET_KEY`, purpose and address | Mitigated |

### 7.2 Tampering

| ID | Threat | Control | Status |
|---|---|---|---|
| T-T1 | Altering ciphertext at rest or in transit | AEAD tag; the server also verifies SHA-256 before serving | Mitigated |
| T-T2 | Relabelling a file's name, MIME type, size or algorithm | All bound into AAD-3; any change fails authentication ([FILE_ENVELOPE.md](crypto/FILE_ENVELOPE.md)) | Mitigated |
| T-T3 | Replacing a user's key envelopes with garbage to lock them out | Rewrap, key addition and passphrase reset all require an RSA-PSS signature by the account private key, each under its own domain label | Mitigated |
| T-T4 | **Rolling back** a key bundle, protection profile or file to an earlier valid version | Optimistic revisions stop concurrent writers, but the client does not pin what it last saw | Open — a malicious server can serve an older valid state. Step 3. |
| T-T5 | Malicious dependency version | Lockfiles; `@noble/ciphers` chosen for zero transitive dependencies | Partial — no provenance or audit gate. Step 4. |
| T-T6 | Rewriting the audit log consistently | Hash chain; HMAC-signed chain-head checkpoints to object-locked storage, HMAC key never given to the backend | Mitigated inside the lock window |
| T-T7 | Tampering with an execution package during offline recovery | Server rechecks identities, lengths and the live grant before accepting the rewrap | Partial — the offline workstation is procedural (TB8) |

### 7.3 Repudiation

| ID | Threat | Control | Status |
|---|---|---|---|
| T-R1 | A user denies having shared, downloaded or reset | Every such action appends an audit event with actor, target, IP and user agent in the same transaction | Mitigated |
| T-R2 | An operator denies altering records | External HMAC checkpoints (T-T6) | Partial — covers the chain head, not who ran what on the host |
| T-R3 | A recovery officer denies approving or executing | Approval and execution are separate audited events; a requester cannot review their own request | Partial — one officer may both approve and execute ([SECURITY_FLOWS.md § Offline Recovery](SECURITY_FLOWS.md#offline-recovery-boundary)) |

### 7.4 Information disclosure

| ID | Threat | Control | Status |
|---|---|---|---|
| T-I1 | Database or disk theft exposes file contents | Nothing on the server opens a DEK (O1) | Mitigated |
| T-I2 | Database theft enables **offline passphrase guessing** | Argon2id at 64 MiB and 3 iterations; minimum 10 characters | Partial — strength depends on the passphrase. Benchmarked and argued in step 2. |
| T-I3 | Metadata leakage: filenames, sizes, sharing graph | None beyond access control | Accepted (N2); the encrypted-manifest decision is step 3 |
| T-I4 | **XSS steals tokens** from `localStorage` | CSP `script-src 'self' 'wasm-unsafe-eval'`, `object-src 'none'`, `frame-ancestors 'none'`. Vue escapes interpolation; the only two `v-html` sinks render bundled content — the logo SVG and the static knowledge-base articles, which `render-knowledge-content.ts` escapes before formatting — so no user- or server-supplied string reaches them today. | Partial — any future XSS reads both tokens. It still cannot extract the private key: it is held as a non-extractable `CryptoKey` and relocks after 15 idle minutes. It *can* use the key to decrypt while it is unlocked. |
| T-I5 | Secrets in logs | Documented exclusion list; `repr=False` on secret fields; [OBSERVABILITY § 7](OBSERVABILITY_AND_INCIDENT_RESPONSE.md#7-verification-that-sensitive-data-stays-out) | Mitigated |
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
| T-E5 | Code reaches production without review | `main` auto-deploys; CI exists, but `main` has **no branch protection**, so any collaborator can push directly and skip review and CI | Open — step 4 |
| T-E6 | Running application reaches the host | Unprivileged `fypapp` service user; loopback-only binding | Partial — no container or systemd sandboxing is claimed here |

## 8. Abuse cases

Worked end-to-end, each names the threats it chains.

1. **Stolen laptop session.** X2 opens the site with a live token. They can list files and
   metadata (T-I3) but cannot decrypt without the passphrase or key file, and cannot reset the
   passphrase without the key file (T-E3). *Residual:* metadata exposure until the session
   expires or is revoked.
2. **Leaked database dump.** X3 has every envelope. Files are safe (T-I1). The attacker runs an
   offline dictionary against each account's Argon2id envelope (T-I2). *Residual:* weak
   passphrases fall; strong ones do not. Step 2 quantifies "strong".
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

## 9. Planned sections

Filled in by the next steps of Issue #60.

| Step | Section | Issue #60 criterion |
|---|---|---|
| 2 | Argon2id measured on supported clients; justification of the 10-character minimum | 2 |
| 3 | PEM export custody and lost-passphrase limits; rollback, recovery-key substitution, fingerprint and revision pinning, independent trust anchor; encrypted-manifest decision and residual metadata leakage | 3, 4, 5 |
| 4 | Dependency and supply-chain policy, CSP exceptions, upload abuse, token storage, offline recovery operations; findings register with severity, disposition and evidence | 6, 7 |

## 10. Revision history

| Version | Change |
|---|---|
| 0.1 | Objectives, non-goals, assets, actors, trust boundaries, STRIDE analysis, abuse cases. |
