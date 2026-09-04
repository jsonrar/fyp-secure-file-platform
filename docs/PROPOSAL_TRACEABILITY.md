# Proposal-to-Delivery Traceability

Audited on **2026-09-04** against the FIT3161 MCS21 Project Proposal Report, GitHub `main`,
all pull requests and commits, current repository tests, and the public staging deployment.
This is an evidence map, not a claim that every completed implementation has received final
academic or independent-security approval.

The live source of truth is the
[SecureView Development Board](https://github.com/users/Waldo0926/projects/1). Its views separate
active backlog, proposal WBS, milestones, acceptance criteria, PR evidence, and direct CT work
packages. The audit imported **49 PR records** (48 merged and one open), retained the ten active
Issue records, and added proposal/commit traceability for work that was not represented by a PR.

## Status rules

| Status | Evidence rule | Completion value |
| --- | --- | ---: |
| Backlog | Required by the proposal, but no implementation/test artefact was found | 0% |
| Ready | Defined and prioritised, but implementation has not started | 10% |
| In progress | Partial implementation or evidence exists; acceptance is not complete | 50% |
| In review | Implementation exists, but an explicit review/sign-off artefact is missing | 90% |
| Done | Repository/deployment evidence satisfies the stated work package | 100% |

Commits are evidence for work packages; they are not treated as 150 independent tasks. GitHub
Issues and PRs share one number sequence, so the repository currently has **52 PRs**, not 62:
48 merged, one open, and three closed without merge. `main` contains 150 commits, including 89
non-merge commits.

## Proposal WBS audit

| WBS | Work package | Status | Primary evidence or remaining gap |
| --- | --- | --- | --- |
| 1.1 | Functional and non-functional requirements | Done | Proposal Sections 3–4; `docs/PROJECT_SCOPE.md`; PR #62 |
| 1.2 | Scope definition and supervisor review | Done | Assessed proposal and maintained scope; meeting/verbal evidence remains outside GitHub |
| 1.3 | Goals and core vision | Done | README goal and deployed product |
| 2.1 | Competitive analysis | Done | Proposal background study and selected differentiators |
| 2.2 | Privacy and OWASP threat modelling | In progress | Implemented controls; formal assessment and independent review remain in Issue #60 |
| 2.3 | Target users and stakeholders | Done | Proposal stakeholders and implemented user/RBAC roles |
| 3.1 | UI/UX and Figma prototypes | Done | Implemented/deployed user journeys and PR #46 |
| 3.2 | REST API and FastAPI module design | Done | `docs/API_DESIGN.md` and public OpenAPI/Swagger contract |
| 3.3 | MySQL schema and migration design | Done | Alembic revision 0006, production SQL, PRs #1 and #24 |
| 3.4 | AES/RSA hybrid workflow design | Done | `docs/SECURITY_FLOWS.md` and authenticated envelope implementation |
| 3.5 | Educational-page design | Done | `/education`, algorithm explorer, playground and knowledge search |
| 4.1 | Vue frontend | Done | Vue 3/TypeScript application, tests, typecheck and build |
| 4.2 | FastAPI backend modules | Done | Auth, keys, files, sharing, audit, admin and recovery APIs |
| 4.3 | MySQL and Alembic implementation | Done | MySQL 8.4 staging, migrations and least-privilege production SQL |
| 4.4 | AES-GCM encryption | Done | Browser AES-128/192/256-GCM and CT-1.7 |
| 4.5 | RSA-OAEP key wrapping | Done | Owner/recovery/recipient DEK wrapping; PR #34 |
| 4.6 | SHA-256 and tamper detection | Done | Authenticated envelope, download verification and integrity UX |
| 4.7 | Argon2id and protected private keys | Done | Password hashing and browser-protected account-key bundles |
| 4.8 | RBAC and session management | Done | Server enforcement, refresh rotation, logout and invalidation; Issue #55 covers richer UI |
| 4.9 | Audit logging | Done | Hash-chained events, per-file history and corrected visibility rules |
| 5.1 | Functional and end-to-end testing | In progress | Live MVP test passed; required browser/MySQL CI and failure paths remain in Issues #53/#58 |
| 5.2 | Cryptographic correctness testing | Done | Primitive, envelope, tamper, upload/download and live integration tests |
| 5.3 | OWASP and security testing | In progress | Hardening/regression tests exist; systematic review remains in Issue #60 |
| 5.4 | Non-expert usability testing | Backlog | No moderated study artefact was found; define tasks, participants, metrics and findings |

**WBS summary:** 20 Done, 3 In progress, 1 Backlog. The simple board completion average is
89.6%; this is a tracking indicator, not an assessment mark or effort-weighted earned value.

## Milestone audit

| Milestone | Status | Evidence or exit condition |
| --- | --- | --- |
| M1 Scope finalised | Done | Assessed proposal and maintained scope artefacts |
| M2 REST API contract | Done | Documented and live OpenAPI contract |
| M3 Figma prototypes reviewed | In review | Interfaces are implemented; attach/export the Figma and explicit sign-off evidence |
| M4 Core cryptographic modules | Done | AES, RSA, SHA/integrity, Argon2id and ChaCha20 implementations/tests |
| M5 Feature freeze | Done | Browser MVP complete; remaining work explicitly classified as hardening/assurance |
| M6 Full system integration | Done | Public HTTPS stack and live two-account MVP test |
| M7 Final demo readiness | In progress | Close/accept P0 CI, MySQL and backup blockers; complete usability and progress-pipeline evidence |

## Product acceptance audit

| Criterion | Status | Evidence or remaining gap |
| --- | --- | --- |
| AC1 Registration and protected RSA private key | Done | Browser key generation and protected private-key bundle |
| AC2 Algorithm choice and ciphertext-only upload | Done | Selectable authenticated ciphers and client-side encryption |
| AC3 Recipient decrypts with own passphrase | Done | Recipient-key rewrap and live two-account proof |
| AC4 Tamper detection before successful decrypt | Done | Authenticated decryption/integrity refusal and UI error |
| AC5 Timestamped actor/access audit | Done | Upload/download/share/revoke events and per-file history |
| AC6 Interactive crypto education | Done | AES/RSA/SHA/Argon2id content and playgrounds |
| AC7 Dismissible four-stage progress pipeline | In progress | Per-file spinner/result exists; inspection→encryption→upload→complete stages and dismissal do not |

## Immediate evidence priorities

1. Make CI and MySQL 8.4 integration suites required and non-skippable (Issues #52 and #53).
2. Prove encrypted off-server backup plus clean-host restore (Issue #56).
3. Conduct and document non-expert usability testing (WBS 5.4).
4. Implement the exact four-stage, dismissible processing feedback required by AC7.
5. Attach the Figma/supervisor-review artefact before changing M3 from In review to Done.

These records should be updated in the same PR that changes their evidence. A runtime change is
not Done until the merged SHA is deployed and the affected live path is verified.
