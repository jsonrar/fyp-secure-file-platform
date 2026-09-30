# Proposal-to-Delivery Traceability

Originally audited on **2026-09-05** against the FIT3161 MCS21 Project Proposal Report, GitHub
`main`, all pull requests and commits, current repository tests, and the public staging
deployment. Repository and board records were rechecked on **2026-09-07**; that record-only
update did not re-verify the public deployment.

This is an evidence map, not a claim that every completed implementation has received final
academic or independent-security approval.

The live source of truth is the
[SecureView Development Board](https://github.com/users/Waldo0926/projects/1). Its five team views
separate active backlog, proposal WBS, milestones, acceptance criteria, and PR evidence. The PR
evidence view contains all 56 merged pull requests plus open PR #49; closed, unmerged PRs #2,
#3, and #17 are intentionally excluded because they did not deliver code. Historical
direct-to-`main` CT work remains attributed by the exact commit table below and the archived
crypto-track record rather than a personal board view or fabricated PR history.

## Status rules

| Status | Evidence rule | Completion value |
| --- | --- | ---: |
| Backlog | Required by the proposal, but no implementation/test artefact was found | 0% |
| Ready | Defined and prioritised, but implementation has not started | 10% |
| In progress | Partial implementation or evidence exists; acceptance is not complete | 50% |
| In review | Implementation exists, but an explicit review/sign-off artefact is missing | 90% |
| Done | Repository/deployment evidence satisfies the stated work package | 100% |

Commits are evidence for work packages; they are not treated as independent tasks. GitHub
Issues and PRs share one number sequence, so the repository currently has **60 PRs**, not 70:
56 merged, one open, and three closed without merge. The rechecked `adbf3cf` `main` baseline
contains 167 commits.

## Proposal WBS audit

| WBS | Work package | Status | Primary evidence or remaining gap |
| --- | --- | --- | --- |
| 1.1 | Functional and non-functional requirements | Done | Proposal Sections 3–4; `docs/PROJECT_SCOPE.md`; PR #62 |
| 1.2 | Scope definition and supervisor review | Done | Supervisor reviewed the MVP demonstration, signed the submitted proposal material, accepted the checkpoint, and assessed the whole project as approximately 70–80% complete at that time |
| 1.3 | Goals and core vision | Done | README goal and deployed product |
| 2.1 | Competitive analysis | Done | Proposal background study and selected differentiators |
| 2.2 | Privacy and OWASP threat modelling | In progress | [THREAT_MODEL.md](THREAT_MODEL.md) v0.1: assets, actors, trust boundaries, non-goals and STRIDE; Argon2id benchmarks, cryptographic trust-anchor decisions, supply chain and the findings register remain in Issue #60 |
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
| 4.8 | RBAC and session management | Done | Server enforcement, refresh rotation, logout revocation (#89), and role-aware admin/recovery UI (#55) |
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
| M3 Figma prototypes reviewed | Done | Supervisor reviewed the MVP/UI demonstration, signed the submitted material, accepted the checkpoint, and assessed the whole project as approximately 70–80% complete at that time; the interfaces are now also implemented and deployed |
| M4 Core cryptographic modules | Done | AES, RSA, SHA/integrity, Argon2id and ChaCha20 implementations/tests |
| M5 Feature freeze | Done | Browser MVP complete; remaining work explicitly classified as hardening/assurance |
| M6 Full system integration | Done | Public HTTPS stack and live two-account MVP test |
| M7 Final demo readiness | In progress | Close/accept P0 CI, MySQL and backup blockers; complete usability and progress-pipeline evidence |

**Milestone summary:** 6 Done and 1 In progress. The supervisor's 70–80% assessment is evidence
for the completed historical checkpoint, not a claim that the current repository has an exact
70–80% completion value.

## Chen Tai cryptography contribution traceability

The nine CT work packages were delivered directly to `main` before the team adopted reviewed
pull requests. They are already ancestors of current `main`; they must not be cherry-picked or
merged again. The shared table below attributes every package to **Chen Tai** through its exact
commit; `changelog/work-packages/crypto-track.md` remains a read-only historical archive. New CT
and other contributor work belongs in the team changelog, README, and TODO rather than a separate
personal tracking view.

| Package | Verified scope | Commit |
| --- | --- | --- |
| CT-1.0 | Prepared the cryptography development environment and documentation; no application or cryptography implementation changed | [`9593e753`](https://github.com/jsonrar/fyp-secure-file-platform/commit/9593e753ecadfcc37f3afb56c5f1f92bf3aaea29) |
| CT-1.1 | Audited the existing cryptography baseline and recorded limitations; no new primitive was implemented | [`99e2f972`](https://github.com/jsonrar/fyp-secure-file-platform/commit/99e2f972862c55d5f39d066152bb491cac8164bc) |
| CT-1.2 | Implemented browser cryptographic primitives | [`415202e6`](https://github.com/jsonrar/fyp-secure-file-platform/commit/415202e661b8c8da30b40458424a8361d6febdb5) |
| CT-1.3 | Defined and validated the encrypted-file envelope | [`9f89ea56`](https://github.com/jsonrar/fyp-secure-file-platform/commit/9f89ea56867ec086f1d2a721942a10c4868a128d) |
| CT-1.4 | Completed encrypted browser upload | [`8e174c6e`](https://github.com/jsonrar/fyp-secure-file-platform/commit/8e174c6e10ff601e06b8f60243ec8b64e8369380) |
| CT-1.5 | Provisioned recovery-key wrapping | [`f3c36a20`](https://github.com/jsonrar/fyp-secure-file-platform/commit/f3c36a20aa88fd8395b224a9b495d745dc1be62e) |
| CT-1.6 | Connected the encrypted-file list | [`aa4e8589`](https://github.com/jsonrar/fyp-secure-file-platform/commit/aa4e858965c61af06e2390bff2a8d55092abfd84) |
| CT-1.7 | Added selectable AES key lengths | [`e04f5fcd`](https://github.com/jsonrar/fyp-secure-file-platform/commit/e04f5fcdd170e1dad2c62b91139af93a02da97fe) |
| CT-1.8 | Added ChaCha20-Poly1305 | [`6c8821a5`](https://github.com/jsonrar/fyp-secure-file-platform/commit/6c8821a5dd00edc58b8c6dce7ef7a5bad749b4a9) |

Current-code regression evidence is stronger than the historical commit messages alone: the
targeted frontend primitive, envelope, upload, download and sharing suite passes **147 tests**,
and the targeted backend migration/model/production-SQL suite passes **10 tests**. This does not
replace the remaining required CI, browser E2E, MySQL or independent-security evidence.

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

These records should be updated in the same PR that changes their evidence. A runtime change is
not Done until the merged SHA is deployed and the affected live path is verified.
