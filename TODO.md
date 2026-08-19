# Project TODO

English | [简体中文](TODO.zh-CN.md)

Last reviewed: 2026-08-15

Priorities:

- **P0:** blocks a trustworthy release or demo.
- **P1:** completes the browser experience for the implemented backend contract.
- **P2:** CI, operations, and production hardening.

## Verified Baseline

- [x] The backend implements authentication, account-key custody/rotation, encrypted files,
  sharing/revocation, integrity, audit queries/verification, governed recovery, and admin
  status controls. Business endpoints are real handlers, not draft responses.
- [x] Account cryptography follows the client-custody boundary:
  - the login password and encryption passphrase are independent;
  - the client generates RSA keys and a random AMK;
  - Argon2id derives a KEK that AES-256-GCM wraps the AMK;
  - an AMK/HKDF-derived key AES-256-GCM encrypts the PKCS8-DER private-key bundle; and
  - the backend never accepts a passphrase, plaintext private key, AMK, plaintext DEK, or
    plaintext file.
- [x] File encryption/decryption and share rewrapping are client operations. The backend
  stores/verifies ciphertext and persists recipient-specific RSA-OAEP-SHA256 DEK wrappings.
- [x] Recovery-private-key use is outside the web service. The API supplies an execution
  package and accepts only an offline/HSM-produced target-key-wrapped DEK.
- [x] Application routes and clients use only `GET` and `POST`; state changes use explicit
  `POST` action paths, and CORS is restricted to those methods.
- [x] Alembic head and the application readiness marker are
  `0004_email_verification_codes`. The reviewed empty-database SQL contains 16 application
  tables and grants ordinary CRUD on 14 state tables, with narrower audit-table grants.
- [x] Registration and login-password reset are gated by emailed one-time codes. Codes are
  stored only as keyed digests, expire, are single use, are attempt-bounded, and are rate
  limited per address and per IP. The send endpoint does not reveal whether an address has
  an account. Reset never touches the key-protection profile or private-key bundle, so it
  cannot cost an account access to its encrypted files.
- [x] English and Simplified Chinese API, architecture, security-flow, schema, deployment,
  and project-scope documentation describe the current scheme and metadata/threat limits.
- [x] Current local verification: Ruff passes; backend tests report `212 passed` with the
  MySQL integration tests actually running against disposable MySQL 8.4; the frontend
  production build passes; and OpenAPI has 47 operations, all `GET`/`POST`, with bearer
  security on protected routes and no passphrase or `private_key_pem` fields.
- [x] The production SQL path and the development migration path were both exercised on
  disposable MySQL 8.4: `01/02/03` reports every status `OK` with no deviation rows, and
  `0001 -> 0004` upgrades, passes `alembic check`, and round trips through `0003` cleanly.
- [x] Sensitive account-key mutations require possession of the newest current private key:
  both successor-key addition and protection-profile rewrap use server-defined canonical
  32-byte digests and client RSA-PSS-SHA256 signatures in addition to bearer authentication.
- [ ] The disposable MySQL 8.4 integration/release gate has been run locally but still needs
  to run in CI. The integration tests require `AUTH_TEST_DATABASE_URL` and must not be
  treated as passing when skipped.
- [ ] The frontend still needs the complete client-cryptography and session UX described
  below. Backend completion does not make the existing browser UI production-ready.
- [ ] The repository still needs a CI workflow and reproducible frontend type/lint/test gates.

## P0 — Release and Demo Blockers

### MySQL 8.4 and Release Verification

- [ ] Exercise the complete development migration path on disposable MySQL 8.4:
  - empty database through `alembic upgrade head`;
  - an explicit `0001 -> 0002 -> 0003` upgrade fixture;
  - `alembic current` and `alembic check`; and
  - revision-0003 preflight refusal for incompatible legacy rows.
- [ ] Exercise the production path on a separate empty MySQL 8.4 instance:
  `01-provision.sql -> 02-schema.sql -> 03-verify.sql`.
  - Inspect every verification result rather than only the client exit code.
  - Prove exact 15-table structure, indexes/checks/foreign keys, the 13-table CRUD matrix,
    narrow audit grants, no migrator/elevated grants, and both revision-0003 markers.
  - Prove non-empty-schema refusal, remote-host substitution, and stale-migrator detection.
- [ ] Prove ORM/Alembic/production-SQL schema parity in automation.
- [ ] Document and rehearse partial-DDL recovery, writer drain, serialized upgrades, bounded
  metadata-lock waits, and verified restore from backup.
- [ ] Decide the fate of every unmanaged legacy database: recreate disposable instances or
  use a separately reviewed adoption/DBA upgrade. Never bypass guards with blind stamping or
  by rerunning the empty-database installer.

### Browser Session and Client Cryptography

- [ ] Implement the complete browser session lifecycle:
  - adopt an explicit access/refresh storage threat model;
  - restore with `/auth/me`, serialize refresh rotation, and avoid `401` retry loops;
  - call server logout and clear revoked/expired state; and
  - add logout-all, password change, session listing/revocation, and role-aware navigation.
- [x] Replace the old registration UX with client-side account-key enrollment:
  - collect a separate strong encryption passphrase without sending it to the server;
  - generate the configured RSA key pair and random AMK locally;
  - produce the Argon2id/KEK-wrapped AMK and AMK/HKDF-encrypted PKCS#8 bundle;
  - self-test passphrase unlock and envelope round trip before registration; and
  - clearly explain that a forgotten passphrase cannot be reset by the server.
  Implemented in `frontend/src/utils/account-crypto.ts`. The self-test proves the stored
  envelopes reopen to the same PKCS#8 bytes; it does not yet re-derive the public key from
  the decrypted private key to check correspondence independently.
- [ ] Implement key-unlock and passphrase-change UX using `GET /keys/me`,
  `POST /keys/me/rewrap/signing-payload`, local newest-current-private-key
  RSA-PSS-SHA256 signing, and `POST /keys/me/rewrap`, including optimistic-revision/current-
  key conflicts, exact proposal reuse between both calls, and safe in-memory cleanup.
- [ ] Implement successor-key rotation with `POST /keys/add/signing-payload`, local
  RSA-PSS-SHA256 signing, `POST /keys/add`, and historical-bundle retrieval through
  `GET /keys/me/{key_id}`. Do not present this as an AMK/passphrase reset.
- [ ] Prevent passphrases, plaintext private keys, AMKs, DEKs, token values, and decrypted
  content from entering logs, analytics, crash reports, URLs, persistent browser storage, or
  service-worker caches.

### Frontend Contract and Tooling

- [ ] Align all frontend API types and views with the implemented UUID-based backend:
  - common response/error envelope and stable error codes;
  - canonical Base64 crypto envelopes and optimistic revisions;
  - multipart ciphertext upload and streamed ciphertext download;
  - target user/key UUID sharing contracts; and
  - bounded pagination for files, audit, recovery, and admin views.
- [ ] Generate or contract-test TypeScript types from OpenAPI to prevent drift.
- [ ] Pin compatible dependency versions, use `npm ci`, restore a passing typecheck, and add
  frontend lint/unit/component/browser-E2E gates.

## P1 — Browser Completion for Implemented Backend Flows

### Encrypted Files

- [x] Backend: bounded multipart ciphertext upload, safe metadata validation, active owner and
  recovery key validation, staged publish/compensation, metadata/grant/wrapping transaction,
  and audit append.
- [x] Backend: authorized file pagination and metadata with the caller-specific wrapped DEK.
- [x] Backend: ciphertext-only download with storage-hash verification, safe disposition, and
  no-store headers; no private key is submitted to the server.
- [x] Backend: owner soft deletion, grant/wrapping revocation, idempotent object cleanup, and
  explicit integrity-check results.
- [ ] Frontend: encrypt with fresh AES-256-GCM DEK/nonce and stable versioned AAD, wrap the DEK
  to owner and recovery public keys, upload ciphertext, and display actionable failures.
- [ ] Frontend: unlock the correct current/historical private-key bundle, unwrap the DEK,
  authenticate/decrypt locally, and save the result without persistent plaintext staging.
- [ ] Frontend: implement real list/detail/delete/integrity UX instead of placeholder data.

### Sharing and Revocation

- [x] Backend: SHARE/REVOKE authorization requires both active grant and wrapping; target
  public-key association and RSA ciphertext length are validated.
- [x] Backend: share creates/reactivates the target grant and wrapping atomically; revoke
  revokes both, is retry-safe, and forbids revoking the canonical owner.
- [x] Backend: delegated share capabilities are attenuated to the acting grant; the canonical
  owner grant is immutable, and only a manager or the existing grantor may update/reactivate
  an existing non-owner grant.
- [x] Backend: shared-user listing returns public UUIDs and bounded capability fields.
- [ ] Frontend: fetch the recipient active public key, locally unwrap/rewrap the DEK, submit
  sharing capabilities, list recipients, and expose confirmation-based revoke controls.
- [ ] Add security telemetry for denied sharing/revocation attempts without leaking whether
  an inaccessible file, user, or key exists.

### Audit and Recovery

- [x] Backend: ciphertext SHA-256 integrity history, actor/file-scoped redacted audit queries,
  and ADMIN full-chain/head verification using the canonical persisted payload.
- [x] Backend: ADMIN recovery-public-key registration/rotation/revocation; 24-hour conditional
  recovery requests; requester/reviewer separation; approve/reject/cancel; execution package;
  and idempotent identical-result execution.
- [x] Backend: recovery create/package/execute require a live downloadable grant and active user
  wrapping (including for owners); execution changes only the target wrapping and never creates,
  revives, or elevates a revoked/reduced grant. Packages cached before revocation cannot be
  clawed back and remain an operational custody boundary.
- [ ] Frontend/admin UX: typed recovery request and reviewer flows, isolated execution-package
  transfer, status/expiry display, and safe error handling.
- [ ] Operations: provision and back up recovery private keys in offline/HSM custody, retain
  historical keys for old file wrappings, authenticate operators, and rehearse recovery.

### Admin and RBAC

- [x] Backend: explicit ADMIN and RECOVERY_OFFICER dependencies, bounded user/file views,
  account enable/disable commands, session revocation on disable, and audit events.
- [ ] Frontend: enforce the same role policy in navigation and replace placeholder admin cards
  with typed user, file, audit, and recovery views.

## P2 — Quality, Operations, and Hardening

### Testing and CI

- [ ] Add a CI workflow for backend format/lint/tests, OpenAPI method policy, migration drift,
  production SQL verification/parity, and frontend build/type/lint/test.
- [ ] Add real multi-connection MySQL tests for throttle locks, refresh replay, session limits,
  key-addition races, sharing/recovery races, and audit-chain serialization.
- [ ] Add failure-injection coverage for storage publish/cleanup, transaction rollback, invalid
  envelopes/signatures, optimistic revision conflicts, and recovery idempotency.
- [ ] Add frontend unit/component and browser E2E tests for enrollment, login/refresh, unlock,
  upload/download, key rotation, share/revoke, recovery, and role denial.
- [ ] Add coverage reporting with reviewed thresholds; skipped integration tests are not a
  release pass.

### Operations and Data Protection

- [x] `/health/live` and `/health/ready` exist; readiness checks database connectivity and the
  exact `0004_email_verification_codes` application schema marker without migrating.
- [ ] Add edge rate limits and a trusted proxy boundary before accepting forwarded IPs.
- [ ] Add cleanup/reconciliation jobs for expired sessions/refresh tokens/throttle buckets,
  stale staged objects, orphaned ciphertext, and expired recovery requests.
- [ ] Automate encrypted database/object backups, retention, restore drills, and RPO/RTO;
  remember that database theft enables offline passphrase guessing and exposes metadata.
- [ ] Define production deployment for API, frontend, TLS termination, persistent ciphertext
  storage, secrets, recovery custody, and storage backup/restore; Compose remains local MySQL.
- [ ] Add structured redacted logs, metrics, alerts, and runbooks for authentication abuse,
  storage faults, schema drift, recovery operations, and audit-chain verification.
- [ ] Reject empty production database credentials and source high-entropy secrets from a
  secret manager.
- [ ] Publish signed/HMAC audit checkpoints outside the application database.

### Security Review

- [ ] Benchmark Argon2id parameters on supported clients and document minimum passphrase UX.
- [ ] Specify exact cross-platform AAD and HKDF byte encodings with conformance vectors.
- [ ] Add client fingerprint/revision pinning or an independent trust anchor for detecting
  malicious public-key/bundle rollback and substitution.
- [ ] Decide whether filenames/MIME types should move into the encrypted manifest; current
  metadata, sizes, timestamps, sharing graph, and traffic patterns remain visible.
- [ ] Complete a formal threat model and external review covering browser token/key custody,
  offline guessing, malicious-client envelopes, upload abuse, recovery operations, metadata
  leakage, storage reconciliation, and log redaction.

## Definition of Done

- [x] Backend transport contracts use public UUIDs and exclude plaintext secret/internal IDs.
- [x] Backend authentication, roles, resource policy, uniform denials, transaction ownership,
  storage compensation, conditional/idempotent commands, audit coupling, and stable domain
  errors are implemented for the planned routes.
- [x] Protection rewrap and successor-key addition require canonical current-private-key
  authorization; a stolen bearer session alone cannot perform either key mutation.
- [x] English and Simplified Chinese design/security/schema/deployment documentation are
  synchronized with the client-side encryption boundary.
- [ ] Required MySQL 8.4 integration, concurrency, production-SQL, and parity tests pass in CI.
- [ ] The frontend implements the real cryptographic/API contracts without demo fallbacks and
  passes type, lint, unit, component, build, and browser E2E gates.
- [ ] Release operations, monitoring, backup/restore, offline recovery custody, and security
  review are documented and rehearsed.

## Explicitly Deferred Beyond the Current FYP Scope

Client-side file encryption/decryption, client-held private-key operations, and recipient DEK
rewrapping are **in the current scope** and implemented at the backend contract boundary.
The following remain deferred unless scope changes:

- metadata-hiding/anonymity and defense against an actively malicious server without an
  independent client trust anchor;
- safe new-AMK reset/version migration after a forgotten encryption passphrase;
- production KMS/HSM implementation and automated clean-room recovery infrastructure;
- Google Drive-style collaboration, real-time editing, encrypted full-text search, and
  large-scale cloud-storage optimization;
- guaranteed support for very large files such as 1 GB+;
- forced deletion of data already copied by a recipient or DRM/non-removable watermarking;
  and
- password reset, email verification, MFA, and external federation without trusted external
  channels.
