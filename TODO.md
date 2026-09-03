# SecureView Prioritized Backlog

[English](TODO.md) | [简体中文](TODO.zh-CN.md)

Updated 2026-09-03 from GitHub `main`, the shared changelog, the repository tests, and the
live staging deployment. GitHub Issues are the executable backlog; this file is the
prioritized summary and must link to them rather than becoming a second, drifting list.

## Shipped MVP baseline

- [x] Email-code registration and login-password reset, real login/logout, refresh rotation,
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

- [ ] [#52 Establish required CI quality gates and fix the current Ruff baseline](https://github.com/jsonrar/fyp-secure-file-platform/issues/52)
  — backend/frontend checks must run on every PR and protect `main`.
- [ ] [#53 Run the full MySQL 8.4 and schema-parity release gate in CI](https://github.com/jsonrar/fyp-secure-file-platform/issues/53)
  — skipped MySQL tests must fail the required job, including migration/production-SQL parity.
- [ ] [#56 Automate encrypted off-server backups and prove clean-host restore](https://github.com/jsonrar/fyp-secure-file-platform/issues/56)
  — define RPO/RTO, coordinate database/ciphertext backups, and retain restore evidence.
- [x] [#61 Keep README, TODO, Issues, changelog, PRs, and deployments synchronized](https://github.com/jsonrar/fyp-secure-file-platform/issues/61)
  — this synchronization PR installs the shared records and evidence checklist; future changes
  use the same rule.

## P1 — complete implemented backend capabilities and operations

- [ ] [#54 Complete browser passphrase change and successor-key rotation](https://github.com/jsonrar/fyp-secure-file-platform/issues/54)
  — use the signed backend contracts and publish a normative account-envelope specification.
- [ ] [#55 Complete admin, recovery-officer, and audit-verification workflows](https://github.com/jsonrar/fyp-secure-file-platform/issues/55)
  — make existing RBAC/recovery/audit APIs demonstrable through role-aware UI.
- [ ] [#57 Validate and enable the staging reconciliation timer safely](https://github.com/jsonrar/fyp-secure-file-platform/issues/57)
  — review report-only output before scheduled deletion is enabled.
- [ ] [#58 Expand browser E2E, concurrency, fault-injection, and coverage gates](https://github.com/jsonrar/fyp-secure-file-platform/issues/58)
  — convert skipped/live-path coverage into required repeatable evidence.
- [ ] [#59 Add redacted observability, incident runbooks, and external audit checkpoints](https://github.com/jsonrar/fyp-secure-file-platform/issues/59)
  — make operational and audit failures visible without leaking secrets.

## P2 — formal security assurance

- [ ] [#60 Complete the formal threat model and independent security review](https://github.com/jsonrar/fyp-secure-file-platform/issues/60)
  — cover account envelopes, Argon2id, token/key custody, metadata, recovery, CSP, dependencies,
  and residual trust boundaries without claiming certification.

## Definition of done for each Issue

- The implementation and tests satisfy the Issue acceptance criteria.
- A reviewed PR links the Issue and updates the bilingual changelog.
- README/TODO and other design documents are updated when their statements changed; otherwise
  the PR says why they are `N/A`.
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
