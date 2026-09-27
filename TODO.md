# SecureView Prioritized Backlog

[English](TODO.md) | [简体中文](TODO.zh-CN.md)

Originally synchronized from GitHub `main`, the shared changelog, repository tests, and
the live staging deployment on 2026-09-03. Rechecked against GitHub `main` at `cab44b1`
on 2026-09-07 after the 500 MiB upload-limit change merged; live deployment was not
re-verified in this backlog-only synchronization. GitHub Issues are the executable backlog,
and the [SecureView Development Board](https://github.com/users/Waldo0926/projects/1) is the
shared Kanban view; this file is the prioritized summary and must link to them rather than
becoming a second, drifting list.

The shipped MVP capabilities below remain checked. GitHub Issues are authoritative; unchecked
items below still need product, operations, security-review, or deployment evidence. Partial
work is not marked complete.

The proposal audit is recorded in
[`docs/PROPOSAL_TRACEABILITY.md`](docs/PROPOSAL_TRACEABILITY.md): 20 of 24 WBS packages are
Done, three are In progress, and one is Backlog. Six of seven product acceptance criteria are
Done; the remaining progress-pipeline criterion is In progress. Milestone M3 is Done based on
the supervisor-reviewed and signed MVP/UI checkpoint; the supervisor's 70–80% whole-project
assessment describes that historical checkpoint rather than an exact current completion value.

## Shipped MVP baseline

Local preview for review: How it works now has a six-step, annotated screenshot guide
with manual navigation, optional playback, and enlargement. See
[walkthrough notes](changelog/CHANGELOG.md#homepage-screenshot-walkthrough--首页截图操作引导).
The capture script uses backend fixtures; this does not close
[#58 browser E2E coverage](https://github.com/jsonrar/fyp-secure-file-platform/issues/58)
or provide deployment evidence.

Current GitHub `main` (live deployment not re-verified in this synchronization): Core
Features loops continuously without the wide-screen boundary gap, preserves hover pause, and
shows all cards statically for reduced motion. See [implementation notes](changelog/CHANGELOG.md#landing-hero-and-feature-marquee-polish--首页主标题与功能滚动条打磨).
This UI fix does not close [#58 browser E2E coverage](https://github.com/jsonrar/fyp-secure-file-platform/issues/58);
live deployment and repeatable browser coverage remain separate acceptance work.

- [x] Email-code registration and login-password reset, login plus server-revoking logout,
  backend session-revocation endpoints, refresh rotation,
  session invalidation, account deletion, throttling, Argon2id password hashing, and RBAC.
- [x] Browser-held account-key enrolment, passphrase/private-key-file unlock, idle relock, and
  historical key-bundle retrieval without sending plaintext private keys to the server.
- [x] Browser-side AES-128/192/256-GCM and ChaCha20-Poly1305 file encryption, RSA-OAEP-SHA256
  DEK wrapping, authenticated download/decryption, integrity failures, and encrypted storage.
- [x] Filename search, pagination, owner/shared separation, sharing by recipient-key rewrap,
  recipient list, revocation, notifications, per-file history, and ownership-correct audit
  visibility.
- [x] Conditional recovery and admin APIs, tamper-evident audit chaining, MySQL least-privilege
  production SQL, HTTPS, nginx rate limits, fail2ban, guarded automatic deployment, and
  reconciliation implementation.
- [x] Public staging and evaluation endpoints:
  [application](https://secureview.tech), [Swagger UI](https://secureview.tech/docs), and
  [OpenAPI JSON](https://secureview.tech/openapi.json).
- [x] Public product pages and signed-in account chrome: landing `/`, Education
  (`/education`: algorithms, playground, knowledge), Help (`/help`: How to Use walkthroughs),
  Development Team mosaic under Contact us (`/team`), header active-tab theme colour, and the avatar menu with
  `/profile` and `/settings`. Evidence and rationale live in
  [`changelog/CHANGELOG.md`](changelog/CHANGELOG.md) under `[Unreleased]`.

The reason and evidence for shipped behavior belong in
[`changelog/CHANGELOG.md`](changelog/CHANGELOG.md), not in duplicated historical TODO text.

## Verified pre-synchronization baseline on 2026-09-03

| Gate | Result | Interpretation |
| --- | --- | --- |
| Backend Pytest | 317 passed, 21 skipped, 1 warning | Unit/API pass; real MySQL coverage did not run |
| Frontend Vitest | 233 passed, 18 skipped | Offline suite passes; integration coverage is skipped |
| Frontend typecheck | Pass | `vue-tsc --noEmit` is operational |
| Frontend production build | Pass | Vite production bundle builds |
| Ruff format/check | **Fail** | Four files need formatting; three import blocks fail |
| GitHub Actions | **Absent** | No required CI gate currently protects `main` |
| Schema baseline | `0006_chacha20_poly1305` | 17 production SQL tables |
| Live staging | `a085ae4` (PR #51, before this documentation sync) | `/`, health, docs, schema, and ReDoc return 200 |

A test run with skipped integration tests is evidence about the offline subset only; it is
not a release pass.

## P0 — release and data-protection blockers

- [x] [#52 Establish required CI quality gates and fix the current Ruff baseline](https://github.com/jsonrar/fyp-secure-file-platform/issues/52)
  — `.github/workflows/ci.yml` runs backend (Ruff + non-MySQL pytest with a coverage floor) and frontend (test with coverage/typecheck/build)
  on every PR and push to `main`; the Ruff baseline is fixed, not suppressed. Branch protection still
  needs a repository admin to mark `backend` and `frontend` required — see the PR that introduced this.
- [x] [#53 Run the full MySQL 8.4 and schema-parity release gate in CI](https://github.com/jsonrar/fyp-secure-file-platform/issues/53)
  — the `mysql-gate` job provisions MySQL 8.4 with verified TLS, exercises every migration through
  `0006_chacha20_poly1305`, runs `alembic current`/`check`, runs the whole backend suite (coverage
  floor 82%) and fails on any skipped test, and checks runtime-vs-admin grants and live schema
  parity. The two gaps once deferred here are closed: the migration-lock race now runs 8 randomized
  iterations that must each show one applier and one waiter, and restores are compared by per-table
  `CHECKSUM TABLE` plus a schema fingerprint, proven by a one-row mutation. Still not a long-running
  chaos test.
- [x] [#56 Automate encrypted off-server backups and prove clean-host restore](https://github.com/jsonrar/fyp-secure-file-platform/issues/56)
  — live on staging since 2026-09-24: nightly encrypted sets to Cloudflare R2 (35-day lifecycle,
  30-day bucket lock), a least-privilege backup account, and failure emails. A real set was
  restored on a separate machine with the offline key in 6.97 s and matched the live database
  and files exactly ([docs/BACKUP_AND_RECOVERY.md](docs/BACKUP_AND_RECOVERY.md) §5). Follow-ups:
  time the 4 h whole-service RTO on a fresh VPS, and prune `mcs21-deploy`'s pre-deploy dumps.
- [x] [#61 Keep README, TODO, Issues, changelog, PRs, and deployments synchronized](https://github.com/jsonrar/fyp-secure-file-platform/issues/61)
  — this synchronization PR installs the shared records and evidence checklist; future changes
  use the same rule.

## P1 — complete implemented backend capabilities and operations

- [ ] [#54 Complete browser passphrase change and successor-key rotation](https://github.com/jsonrar/fyp-secure-file-platform/issues/54)
  — use the signed backend contracts and publish a normative account-envelope specification.
- [x] [#55 Complete admin, recovery-officer, and audit-verification workflows](https://github.com/jsonrar/fyp-secure-file-platform/issues/55)
  — `/admin` is role-aware: ADMIN gets users, files, audit-chain verify, recovery-key
  registration, and recovery review; RECOVERY_OFFICER reviews and executes (offline rewrap
  paste-back); ordinary users open requests from My Files and track/cancel them here.
- [x] [#89 Revoke the server session when a user logs out](https://github.com/jsonrar/fyp-secure-file-platform/issues/89)
  — intentional Log out calls `POST /auth/logout` before clearing the browser; expiry and
  account deletion still clear locally only.
- [ ] [#57 Validate and enable the staging reconciliation timer safely](https://github.com/jsonrar/fyp-secure-file-platform/issues/57)
  — repository side done: directory grace, volume guard (exit 3), both-sides boundary report,
  MySQL idempotency and no-audit/key/recovery-statement tests, a 05:00 timer after the same-host
  backup, email alerts, and [docs/RECONCILIATION_RUNBOOK.md](docs/RECONCILIATION_RUNBOOK.md).
  Installed on staging 2026-09-24; report-only review recorded (43 eligible, 0 orphans) and the
  timer enabled. Open: record the first scheduled run (2026-09-25 05:00) and an idempotent re-run.
- [x] [#58 Expand browser E2E, concurrency, fault-injection, and coverage gates](https://github.com/jsonrar/fyp-secure-file-platform/issues/58)
  — the `e2e-live` CI job runs every frontend live-backend suite un-skipped against a
  disposable API and MySQL (registration through account deletion, all four file algorithms,
  role denial), then a Chromium smoke test that clicks the built pages through register,
  verify, sign in, unlock, upload, download, share, revoke and log out; `mysql-gate` runs
  multi-connection concurrency and real fault-injection suites; coverage floors and sanitized
  JUnit/coverage artifacts are in place ([docs/E2E_TESTING.md](docs/E2E_TESTING.md)).
- [ ] [#59 Add redacted observability, incident runbooks, and external audit checkpoints](https://github.com/jsonrar/fyp-secure-file-platform/issues/59)
  — repository implementation is ready: redacted structured events, loopback metrics and threshold alerts, trusted-proxy enforcement, HMAC external audit checkpoints, sparse alert email, and paired incident runbooks. Open until the exact merge SHA is deployed, the external checkpoint is independently verified, and staging redaction/alert evidence is recorded.

## P2 — formal security assurance

- [x] [#90 Add an isolated VPS adversarial tamper drill with integrity evidence](https://github.com/jsonrar/fyp-secure-file-platform/issues/90)
  — a resource-limited attacker container sees only disposable lab volumes and a MySQL 8.4
  `_test` database. It proves `MODIFIED`/`CORRUPTED`, refused download, `MISSING`, recovery to
  `VALID`/`ACTIVE`, and the SHA-256 versus AEAD trust boundary; CI retains a sanitized report
  ([runbook](security-lab/README.md)).

- [ ] [#60 Complete the formal threat model and independent security review](https://github.com/jsonrar/fyp-secure-file-platform/issues/60)
  — cover account envelopes, Argon2id, token/key custody, metadata, recovery, CSP, dependencies,
  and residual trust boundaries without claiming certification.

## P3 — planned product UX

Triaged into executable Issues on 2026-09-07 and placed in the shared backlog. These items are
not treated as closed by nearby UI polish; partial branch implementations are noted below.
Each Issue carries its acceptance criteria under [#61](https://github.com/jsonrar/fyp-secure-file-platform/issues/61).

- [x] [#72 Add secondary confirmation for destructive and high-risk actions](https://github.com/jsonrar/fyp-secure-file-platform/issues/72)
  — file deletion and share revocation use a dedicated consequence dialog; account deletion
  keeps the password + typed-`DELETE` dialog and is available from Profile as well as Settings.
- [ ] [#71 Add authenticated ciphertext preview and encrypted-blob download](https://github.com/jsonrar/fyp-secure-file-platform/issues/71)
  — authorized users can inspect a bounded ciphertext preview or save the opaque stored object
  without silently decrypting it or changing the normal plaintext-download flow.
  Branch `feat/download-encrypted-file` implements the passphrase-free ciphertext download
  for owners and authorized recipients. Preview and deployment verification remain pending;
  this partial implementation does not close #71.
- [ ] [#73 Add file shelves and move-to-shelf organization in My Files](https://github.com/jsonrar/fyp-secure-file-platform/issues/73)
  — create owner-scoped shelves and move owned files between them or root without changing
  encryption, sharing, file identity, or audit semantics.
- [ ] [#54 Complete browser passphrase change, key-file reset, and successor-key rotation](https://github.com/jsonrar/fyp-secure-file-platform/issues/54)
  — the key-file reset is done: Settings verifies the saved private-key file against the
  account public key, re-seals it under a new AMK and passphrase, and proves possession with an
  RSA-PSS signature; plaintext private keys never leave the browser. Still open: changing the
  passphrase while the old one is known, successor-key rotation, and the account-envelope
  specification. This partial implementation does not close #54.
- [ ] [#74 Add persistent English and Simplified Chinese language switching](https://github.com/jsonrar/fyp-secure-file-platform/issues/74)
  — user-selectable product locale with complete key coverage, safe fallback, persistence, and
  mobile-compatible controls.
- [x] [#75 Add validated user avatar upload and display](https://github.com/jsonrar/fyp-secure-file-platform/issues/75)
  — optional profile/header image with content validation, safe serving, cleanup, rate limits,
  and initials fallback. Evidence still required: reviewed PR, staging deploy to the merge SHA,
  and a short upload/display/delete walkthrough before the Issue closes.
- [ ] [#76 Fix mobile and narrow-viewport usability across product flows](https://github.com/jsonrar/fyp-secure-file-platform/issues/76)
  — repair narrow-screen layout and interaction regressions across public, account, and file
  flows, with repeatable mobile browser evidence.

## Definition of done for each Issue

- The implementation and tests satisfy the Issue acceptance criteria.
- A reviewed PR links the Issue and updates the bilingual changelog.
- README/TODO and other design documents are updated when their statements changed; otherwise
  the PR says why they are `N/A`.
- All contributors use the shared changelog; do not create or extend personal or track-specific
  change logs.
- Secret and generated-artifact review passes before merge.
- For runtime changes, automatic deployment reaches the exact merged SHA and health plus the
  affected user-visible flow are verified. Merge alone is not deployment completion.
- The Issue closes only when the evidence above is linked.

## Explicitly deferred beyond the current FYP

- Google Drive-style collaborative editing, encrypted full-text search, and large-scale object
  storage optimization.
- Guaranteed support for files above 1 GB.
- DRM-like prevention of copies already made by recipients.
- Production KMS/HSM implementation and independent certification. Their design and custody
  requirements remain in scope for the security review.
