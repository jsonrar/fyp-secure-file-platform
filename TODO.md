# SecureView Prioritized Backlog

[English](TODO.md) | [简体中文](TODO.zh-CN.md)

Updated 2026-09-03 from GitHub `main`, the shared changelog, the repository tests, and the
live staging deployment; rechecked against the current worktree on 2026-09-05 after the Help
page, header wayfinding, and landing polish landed on the frontend line. GitHub Issues
are the executable backlog, and the
[SecureView Development Board](https://github.com/users/Waldo0926/projects/1) is the shared
Kanban view; this file is the prioritized summary and must link to them rather than becoming
a second, drifting list.

The shipped MVP capabilities below remain checked. The current worktree does not yet satisfy
the complete acceptance goal of any unchecked Issue #52–#60: some have foundations in place,
but CI, operational evidence, or the remaining role-aware UI is still missing. Partial work is
therefore not marked complete.

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

Current local update (deployment pending): Core Features now loops continuously without
the wide-screen boundary gap, preserves hover pause, and shows all cards statically for
reduced motion. See [implementation notes](changelog/CHANGELOG.md#landing-hero-and-feature-marquee-polish--首页主标题与功能滚动条打磨).
This UI fix does not close [#58 browser E2E coverage](https://github.com/jsonrar/fyp-secure-file-platform/issues/58);
live deployment and repeatable browser coverage remain separate acceptance work.

- [x] Email-code registration and login-password reset, login plus local browser logout,
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

## P3 — planned product UX (Issues not opened yet)

Recorded 2026-09-05 as follow-on product work. These items are **not** in progress and must
not be treated as closed by nearby UI polish. Open a GitHub Issue (and board card) before
starting each one so acceptance criteria stay executable under [#61](https://github.com/jsonrar/fyp-secure-file-platform/issues/61).

- [ ] Confirm destructive actions twice before they run
  — e.g. delete file / revoke share / delete account: a dedicated confirm dialog stating what
  is lost, not a one-click icon.
- [ ] Let users preview or download the ciphertext as stored
  — optional “encrypted blob” view/download so a first-time user can see that the uploaded
  object is not the plaintext file.
- [ ] Folders (file shelves) and move-into-folder in My Files
  — create shelves and move owned files between them without changing encryption or share
  semantics.
- [ ] Account settings entry to reset the encryption passphrase with the saved key file
  — require the registration `.pem` (or equivalent private-key file) before replacing the
  passphrase; complements [#54](https://github.com/jsonrar/fyp-secure-file-platform/issues/54)
  and must not send plaintext keys to the server.
- [ ] i18n language switching
  — user-selectable locale for the product chrome (at least English / 简体中文), persisted with
  the theme preference.
- [ ] Avatar upload
  — replace initials-only avatar with an optional user-uploaded image on profile / header,
  with size and type limits.
- [ ] Mobile layout and interaction fixes
  — repair phone/narrow-viewport regressions across the landing, header, walkthrough, file
  flows, and account chrome so the product is usable without a desktop browser.

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
