# Project TODO

English | [简体中文](TODO.zh-CN.md)

Last reviewed: 2026-08-06

This backlog is based on the current code, migrations, tests, and project documentation.
Priorities are ordered as follows:

- **P0:** blocks a trustworthy demo, migration, or deployment.
- **P1:** required to complete the FYP scope.
- **P2:** quality, operations, and production hardening after the core flows work.

## Verified Baseline

- Backend Auth is the only completed business vertical slice.
- The other 18 file, sharing, audit-query, recovery, and admin endpoints remain fail-closed
  with `501 feature_not_implemented`.
- Local backend checks pass: Ruff is clean and `pytest` reports `110 passed, 2 skipped`.
  The skipped tests require a disposable MySQL integration database.
- The frontend production build passes.
- Frontend type-checking currently fails because `typescript@7.0.2` and `vue-tsc@3.3.7`
  are incompatible.
- The repository has no CI workflow.

## P0 — Release and Demo Blockers

### Database and Release Safety

- [ ] Repair and validate Alembic revision `0002_auth_identity_sessions` on MySQL 8.4.
  - Determine whether `0002` has been applied outside disposable development databases;
    add a corrective revision instead of rewriting applied history when necessary.
  - Create a replacement `user_sessions(user_id, status)` index before dropping
    `idx_user_sessions_user_id`, which currently backs `fk_user_sessions_user`.
  - Test both an empty database upgraded to `head` and a real `0001 -> 0002` upgrade.
  - Verify and document recovery from partially committed MySQL DDL.

- [ ] Add a required MySQL 8.4 CI and release gate.
  - Run `alembic upgrade head`, `alembic check`, and schema verification against a
    disposable database.
  - Exercise `0001 -> 0002`, repeated deployment, failure refusal, and
    `provision_mysql -> deploy_mysql -> verify_mysql`.
  - Run the currently skipped MySQL integration tests instead of treating a skip as a
    release pass.

- [ ] Decide the fate of the unmanaged legacy database.
  - Recreate it when it contains no required data.
  - Otherwise back it up and build a reviewed one-time adoption migration.
  - Never use `alembic stamp` merely to bypass the deployment guard.

### Frontend Authentication

- [ ] Remove all demo authentication behavior from `frontend/src/pages/LoginPage.vue`.
  - Delete the hard-coded `admin / 12345678` bypass.
  - Delete `demo-admin-token` and the fallback `demo-token`.
  - Treat a missing or malformed token response as a failed login.

- [ ] Implement the complete browser session lifecycle.
  - Type and store the access/refresh pair according to an explicit browser-storage threat
    model.
  - Restore identity with `/auth/me`, rotate refresh tokens once, and serialize concurrent
    refresh attempts.
  - Handle `401` responses without retry loops, call the server on logout, and clear local
    state on revoked or expired sessions.
  - Add UI support for logout-all, password change, and session listing/revocation.
  - Enforce role-aware navigation so `/admin` is not considered available merely because
    any token exists.

- [ ] Make registration private-key delivery safe and usable.
  - Force a one-time `.pem` download and require the user to acknowledge safe storage.
  - Do not put the private key in `localStorage`, logs, analytics, or error reports.
  - Clearly explain that a lost response/key cannot currently be reproduced.

### Contracts and Frontend Tooling

- [ ] Align frontend and backend contracts before enabling any draft route.
  - Use public UUIDs consistently; remove frontend `number` file/request IDs and sequential
    `target_user_id` API fields.
  - Reconcile sharing's `target_username` frontend payload with the backend request model.
  - Type the common API envelope, stable error codes, pagination, and binary downloads.
  - Mark private-key inputs as secrets, forbid unexpected fields, and apply request-body
    redaction at application, proxy, and tracing layers.
  - Prefer generated or contract-tested TypeScript types from OpenAPI to prevent drift.

- [ ] Stabilize the frontend dependency and quality toolchain.
  - Replace `"latest"` specifications with reviewed compatible versions and use `npm ci`
    for reproducible automation.
  - Resolve the TypeScript/`vue-tsc` incompatibility and add a passing `typecheck` script.
  - Review the current deprecated icon-package warning and moderate npm audit finding
    without automatically applying `npm audit fix --force`.
  - Add `lint` and `test` scripts so build success is not the only frontend gate.

## P1 — Complete the Core FYP Vertical Slices

Enable one router at a time. Keep all other draft routers fail-closed until their acceptance
criteria and denial tests pass.

### File Upload and Encrypted Storage

- [ ] Implement authenticated file upload end to end.
  - Add repository and storage-adapter boundaries instead of putting SQL, filesystem, or
    cryptography in the router.
  - Reject oversized requests before unbounded reads and validate safe filename/type
    metadata.
  - Stream into a versioned AES-256-GCM envelope with a fresh key and nonce per file,
    authenticated metadata (AAD), and no plaintext temporary object.
  - Provision the active recovery public key and define fail-closed behavior when it is
    unavailable.
  - In one use-case transaction, create metadata, owner grant, owner/recovery key wrappings,
    and the audit event.
  - Use staged storage, atomic rename, rollback cleanup, and crash-orphan reconciliation.
  - Add happy-path, size/type rejection, encryption failure, storage failure, rollback, and
    authorization tests.

### File Listing, Download, and Deletion

- [ ] Implement list and metadata endpoints with stable ordering and pagination or a hard
  result bound.
- [ ] Enforce both an active access grant and matching active key wrapping on every download.
- [ ] Implement transient private-key handling on a dedicated no-body-logging path, stream
  the download with safe `Content-Disposition`, and prevent response caching.
- [ ] Make the frontend save the returned blob rather than only reporting that a request was
  sent.
- [ ] Define status-based deletion, encrypted-object cleanup, owner/shared-user behavior,
  idempotency, and audit events; do not hard-delete rows referenced by audit history.

### Sharing and Revocation

- [ ] Implement owner/`SHARE` authorization and lookup by a public account identifier.
- [ ] Require an active target public key, unwrap only transiently, and create the target
  grant plus wrapped key atomically.
- [ ] Make repeated share/revoke commands safe, forbid revoking the canonical owner, and
  revoke both the grant and key wrapping in one transaction.
- [ ] Implement shared-user listing and frontend revoke controls.
- [ ] Audit successful and denied mutations and test cross-user, missing-key, inactive-user,
  duplicate, self-share, and already-revoked cases.

### Integrity and Audit

- [ ] Persist and verify SHA-256 over the encrypted object, not plaintext.
- [ ] Record authorized integrity checks and avoid exposing storage paths or unnecessary
  internal hashes.
- [ ] Implement authorized, paginated audit queries with public identifiers and safe
  metadata.
- [ ] Recompute the complete audit chain using the canonical persisted payload, compare it
  with `audit_chain_heads`, and report the first invalid position safely.
- [ ] Add multi-connection MySQL tests proving concurrent audit writes cannot fork the chain.

### Recovery

- [ ] Define recovery-key provisioning, rotation, deactivation, storage, and demo custody.
- [ ] Enforce maker-checker separation, expiry, permitted state transitions, and idempotent
  execution in service code and database constraints where practical.
- [ ] Constrain each key-wrapping row so its recipient type and nullable user/recovery key
  references form exactly one valid recipient.
- [ ] Isolate recovery private-key use, disable body logging, and audit request, approval,
  rejection, expiry, and execution.
- [ ] Add tests for self-approval, expired requests, repeated approval/execution, wrong roles,
  invalid keys, and rollback.

### Admin and RBAC

- [ ] Implement explicit role dependencies for admin and recovery-approval routes.
- [ ] Implement bounded user/file views using public identifiers and redacted fields.
- [ ] Use status-based account disablement so audit-history foreign keys remain intact.
- [ ] Replace the frontend's recovery-count placeholder with typed admin/recovery workflows
  and enforce the same role policy in navigation and routes.

## P2 — Quality, Operations, and Hardening

### Automated Testing and CI Depth

- [ ] Parameterize fail-closed tests across all 18 draft endpoints until each is deliberately
  enabled.
- [ ] Add service/repository tests for file, access-control, sharing, integrity, recovery,
  and watermark behavior.
- [ ] Add real multi-connection MySQL concurrency tests for throttle row locks, refresh-token
  replay, session limits, sharing races, and audit-chain serialization.
- [ ] Add frontend unit/component tests and browser E2E tests for registration, login,
  refresh, upload, download, share, revoke, recovery, and role denial.
- [ ] Add measurable backend/frontend coverage reporting and reviewed thresholds.

### Frontend UX and Accessibility

- [ ] Remove the display-only AES-128/AES-192/3DES selector; the supported behavior is
  AES-256-GCM.
- [ ] Remove or finish placeholder/inert UI such as `FileTable.vue`, the file filter button,
  synthetic encrypted sizes/dates, and incomplete admin cards.
- [ ] Centralize API-envelope/error handling and show stable, user-safe messages.
- [ ] Add semantic forms, field validation, accessible labels, keyboard/focus handling for
  dialogs, confirmation for destructive actions, and reliable loading/empty/error states.

### Deployment and Data Protection

- [ ] Add `/health/ready` to check MySQL connectivity and the expected Alembic head before
  receiving traffic.
- [ ] Make release orchestration drain/stop application writers before migration, and set
  finite MySQL metadata-lock timeouts plus an overall deployment deadline.
- [ ] Automate encrypted backups/snapshots, record the backup identifier used for a release,
  define retention and RPO/RTO, and run restore drills.
- [ ] Define deployment for the backend, frontend, TLS termination, persistent encrypted-file
  storage, secret injection, and storage backup/restore; the current Compose file deploys
  only MySQL.
- [ ] Add structured redacted logging, metrics, alerts, and runbooks for authentication
  abuse, storage failures, migration failures, and audit-chain verification.

### Security Operations

- [ ] Reject an empty production `DB_PASSWORD` and source high-entropy credentials from a
  secret manager.
- [ ] Reduce runtime database privileges, especially for `alembic_version`, `audit_logs`,
  and `audit_chain_heads`; keep schema changes migration-only.
- [ ] Publish signed/HMAC audit checkpoints outside the application database.
- [ ] Configure a trusted proxy boundary and edge rate limits before trusting forwarded IPs.
- [ ] Add cleanup/retention jobs for expired sessions, refresh credentials, throttle buckets,
  stale staging files, and orphaned encrypted objects.
- [ ] Complete a threat model and security review covering token storage, private-key
  handling, upload abuse, filename/content handling, cryptographic envelopes, recovery, and
  log redaction.

## Definition of Done for Every Vertical Slice

- [ ] Typed request/response contracts expose no secrets or sequential database IDs.
- [ ] Authentication, role checks, resource policy, and denial behavior are explicit.
- [ ] One application service owns the transaction and rollback behavior.
- [ ] Storage compensation and idempotency are defined where applicable.
- [ ] The security-sensitive mutation and its audit event commit together.
- [ ] Stable domain error codes are documented and safely mapped to HTTP.
- [ ] Unit tests plus API/MySQL tests cover happy, denial, conflict, rollback, and concurrency
  paths as applicable.
- [ ] The frontend handles the real contract without demo fallbacks.
- [ ] English and Simplified Chinese documentation are updated together.

## Explicitly Deferred Beyond the Current FYP Scope

Do not expand the core backlog with these unless the project scope changes:

- Full end-to-end encryption and production KMS/HSM integration
- Google Drive-style collaboration or real-time multi-user editing
- Encrypted full-text search and large-scale cloud-storage optimization
- Guaranteed support for very large files such as 1 GB+
- Forced deletion of plaintext copies already downloaded by a recipient
- Fully non-removable watermarking
- Password reset, email verification, MFA, and external identity federation without a
  trusted out-of-band channel
