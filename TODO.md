# Project TODO

English | [简体中文](TODO.zh-CN.md)

Last reviewed: 2026-08-21

Priorities:

- **P0:** blocks a trustworthy release or demo.
- **P1:** completes the browser experience for the implemented backend contract.
- **P2:** CI, operations, and production hardening.

## Verified Baseline

### Backend and cryptographic contract

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
- [x] Sensitive account-key mutations require possession of the newest current private key:
  both successor-key addition and protection-profile rewrap use server-defined canonical
  32-byte digests and client RSA-PSS-SHA256 signatures in addition to bearer authentication.
- [x] Registration and login-password reset are gated by emailed one-time codes. Codes are
  stored only as keyed digests, expire, are single use, are attempt-bounded, and are rate
  limited per address and per IP. The send endpoint does not reveal whether an address has
  an account. Reset never touches the key-protection profile or private-key bundle, so it
  cannot cost an account access to its encrypted files.

### Browser cryptography (CT-1.2 through CT-1.5)

- [x] Browser cryptographic primitives with cross-implementation test vectors:
  `frontend/src/crypto/primitives.ts` and `encoding.ts`.
- [x] A normative file encryption envelope, `docs/crypto/FILE_ENVELOPE.md` plus the locked
  `test_vectors.json`, implemented by `frontend/src/crypto/file_envelope.ts`. The server
  never computes this AAD, so the specification and vectors are the only defence against a
  divergent second implementation.
- [x] The upload path really encrypts. `frontend/src/crypto/upload.ts` fetches the owner and
  active recovery public keys, encrypts with a fresh DEK/nonce, wraps the DEK to both keys,
  and assembles the `file` + `metadata` multipart body the route requires. The unwired
  cipher selector and the "server-side encryption" copy are gone.
- [x] Client-side account-key enrolment replaces the old registration UX
  (`frontend/src/utils/account-crypto.ts`): a separate strong passphrase is collected and
  never sent, RSA keys and the AMK are generated locally, and both envelopes are self-tested
  before registration. The self-test proves the stored envelopes reopen to the same PKCS#8
  bytes; it still does not re-derive the public key from the decrypted private key to check
  correspondence independently.
- [x] Recovery key provisioning: `backend/scripts/register_recovery_key.py` generates the
  pair, writes the private half locally at mode 600, registers only the public half through
  the ADMIN route, refuses to overwrite an existing private key, and verifies the reported
  fingerprint against a locally computed one.
- [x] Independent end-to-end proof: a stored file was decrypted with the offline recovery
  private key, rebuilding AAD-3 in Python from persisted metadata alone. That path touches
  none of the TypeScript, so it confirms both the AAD byte layout and the recovery wrapping —
  the one envelope no client can self-test.

### Database, deployment, and documentation

- [x] Alembic head and the application readiness marker are
  `0004_email_verification_codes`. The reviewed empty-database SQL contains 16 application
  tables and grants ordinary CRUD on 14 state tables, with narrower audit-table grants.
- [x] The production SQL path and the development migration path were both exercised on
  disposable MySQL 8.4: `01/02/03` reports every status `OK` with no deviation rows, and
  `0001 -> 0004` upgrades, passes `alembic check`, and round trips through `0003` cleanly.
- [x] Staging serves over HTTPS behind nginx, the bare IP redirects to the canonical origin,
  and a shared test account is seeded through the real registration path.
- [x] English and Simplified Chinese API, architecture, security-flow, schema, deployment,
  and project-scope documentation describe the current scheme and metadata/threat limits.

### Current local verification (2026-08-21)

- [x] Backend: `235 passed, 5 skipped` with `AUTH_TEST_DATABASE_URL` unset. The five skips
  are the disposable MySQL 8.4 integration tests; a run with them skipped is not a release
  pass.
- [x] Frontend: `110 passed, 3 skipped`. The three skips are `upload.integration.test.ts`,
  which runs only when `E2E_API_BASE` is set, so `npm test` stays offline by default.
- [x] Frontend production build passes.
- [ ] Frontend typecheck does not run at all: `vue-tsc` fails with
  `ERR_PACKAGE_PATH_NOT_EXPORTED` on `typescript/lib/tsc`, because `package.json` pins both
  to `latest` and the resolved pair is incompatible. There is no `typecheck` script.
- [ ] There is no CI workflow. Every gate above is a local, manual run.

## P0 — Release and Demo Blockers

### Download and Decryption (the demo cannot complete without this)

- [x] Implement the real download path. `file-management.vue` used to call
  `fileApi.download(id)`, discard the returned ciphertext, and report "Download request
  sent", so uploaded files could not be read back through the UI. `crypto/download.ts` now
  unwraps, decrypts, and saves.
- [x] Unwrap the caller-specific DEK, rebuild the AAD from the file metadata exactly as
  `docs/crypto/FILE_ENVELOPE.md` defines it, authenticate/decrypt locally, and save the
  plaintext without persistent staging. Nothing reaches disk before the tag authenticates.
- [x] Resolve the historical-key case: a file wrapped to a superseded key needs
  `GET /keys/me/{key_id}` and that bundle's private key, not the current one. Unlocked keys
  are cached by id, and a file wrapped to an unopened key names it and offers to unlock it.
- [x] Surface authentication-tag failures as integrity failures, distinctly from network or
  authorization errors. `FileKeyUnwrapError` and `FileIntegrityError` separate "not your
  key" from "not the bytes that were encrypted", and the second marks the file's row.

### Browser Private-Key Custody and Unlock

- [x] Decide and implement how the private key returns to the browser after registration.
  Decided: it comes back from `GET /keys/me` and is opened with the encryption passphrase,
  not re-imported from the PEM. `UnlockDialog.vue` provides the passphrase UX; the one-time
  PEM download stays an offline backup, which is the open question below.
- [x] Implement unlock: Argon2id from the stored protection profile, AMK unwrap, private-key
  bundle decrypt, an in-memory session-scoped key handle, and explicit clearing on logout
  and tab close. The handle is a non-extractable `CryptoKey` in module scope, so a reload or
  tab close discards it, and `logout()` clears it explicitly.
- [x] Add an idle timeout that relocks the account key. Fifteen minutes without use, reset
  by use rather than by mouse movement.
- [ ] Implement passphrase change using `GET /keys/me`,
  `POST /keys/me/rewrap/signing-payload`, local newest-current-private-key RSA-PSS-SHA256
  signing, and `POST /keys/me/rewrap`, including optimistic-revision/current-key conflicts,
  exact proposal reuse between both calls, and safe in-memory cleanup.
- [ ] Implement successor-key rotation with `POST /keys/add/signing-payload`, local
  RSA-PSS-SHA256 signing, `POST /keys/add`, and historical-bundle retrieval through
  `GET /keys/me/{key_id}`. Do not present this as an AMK/passphrase reset.
- [ ] Prevent passphrases, plaintext private keys, AMKs, DEKs, token values, and decrypted
  content from entering logs, analytics, crash reports, URLs, persistent browser storage, or
  service-worker caches.

### Browser Session Lifecycle

- [ ] Replace the current session handling. `auth_store.ts` keeps only an access token in
  `localStorage`; there is no refresh rotation, no `/auth/me` restore, no server-side logout
  call, and no `401` handling, so an expired token leaves the UI in a broken authenticated
  state.
- [ ] Adopt an explicit access/refresh storage threat model and document it.
- [ ] Restore with `/auth/me`, serialize refresh rotation, and avoid `401` retry loops.
- [ ] Call server logout and clear revoked/expired state.
- [ ] Add logout-all, password change, session listing/revocation, and role-aware navigation;
  the router currently gates only on "a token exists".

### Frontend Contract and Tooling

- [ ] Fix sharing, which is currently non-functional: `ShareDialog.vue` posts
  `{target_username}` while the backend expects a target user UUID and a recipient-wrapped
  DEK. See the sharing item under P1 for the full flow.
- [ ] Align all remaining frontend API types and views with the implemented UUID-based
  backend:
  - common response/error envelope and stable error codes;
  - canonical Base64 crypto envelopes and optimistic revisions;
  - streamed ciphertext download;
  - target user/key UUID sharing contracts; and
  - bounded pagination for files, audit, recovery, and admin views.
- [ ] Pin exact dependency versions instead of `latest`, restore a working `vue-tsc`
  typecheck, add a `typecheck` script, and use `npm ci`.
- [ ] Generate or contract-test TypeScript types from OpenAPI to prevent drift.
- [ ] Add frontend lint, component, and browser-E2E gates alongside the existing unit tests.

### MySQL 8.4 and Release Verification

- [ ] Move the disposable MySQL 8.4 gate into automation. Both paths have been run locally,
  but the integration tests skip silently without `AUTH_TEST_DATABASE_URL`, so nothing
  currently prevents a release on a run where they never executed.
- [ ] Prove ORM/Alembic/production-SQL schema parity in automation.
- [ ] Keep the explicit upgrade fixtures under test: `0001 -> 0002 -> 0003`,
  `alembic current`, `alembic check`, and revision-0003 preflight refusal for incompatible
  legacy rows.
- [ ] Keep the production-path assertions under test: exact table structure, indexes, checks,
  foreign keys, the CRUD matrix, narrow audit grants, absent migrator/elevated grants, both
  revision-0003 markers, non-empty-schema refusal, remote-host substitution, and
  stale-migrator detection. Inspect result sets, not just the client exit code.
- [ ] Document and rehearse partial-DDL recovery, writer drain, serialized upgrades, bounded
  metadata-lock waits, and verified restore from backup.
- [ ] Decide the fate of every unmanaged legacy database: recreate disposable instances or
  use a separately reviewed adoption/DBA upgrade. Never bypass guards with blind stamping or
  by rerunning the empty-database installer.

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
- [x] Frontend: encrypt with a fresh AES-256-GCM DEK/nonce and stable versioned AAD, wrap the
  DEK to the owner and recovery public keys, upload ciphertext, and report per-file outcomes.
  The recovery fingerprint shown in the UI is recomputed locally from the PEM, never read
  from the API response.
- [x] Frontend: decrypt on download, per the P0 item above.
- [ ] Frontend: replace the placeholder file table (`components/FileTable.vue`), show real
  encrypted sizes and timestamps instead of the `-` placeholders in `file-management.vue`,
  and wire delete and integrity-check results into the UI.
- [ ] Frontend: report upload rejections that come from server-side limits distinctly from
  the local 25 MiB pre-check.

### Sharing and Revocation

- [x] Backend: SHARE/REVOKE authorization requires both active grant and wrapping; target
  public-key association and RSA ciphertext length are validated.
- [x] Backend: share creates/reactivates the target grant and wrapping atomically; revoke
  revokes both, is retry-safe, and forbids revoking the canonical owner.
- [x] Backend: delegated share capabilities are attenuated to the acting grant; the canonical
  owner grant is immutable, and only a manager or the existing grantor may update/reactivate
  an existing non-owner grant.
- [x] Backend: shared-user listing returns public UUIDs and bounded capability fields.
- [ ] Frontend: resolve the recipient to a user UUID, fetch their active public key with
  `GET /keys/users/{user_id}/active`, unwrap the DEK locally, rewrap it to the recipient,
  submit sharing capabilities, list recipients, and expose confirmation-based revoke
  controls. This depends on private-key unlock.
- [ ] Frontend: show the recipient key fingerprint before sharing, so a substituted public
  key is visible to the user.
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
- [ ] Frontend: the audit page derives view/download counts from log actions but has no
  chain-verification UI; wire `POST /audit-logs/verify-chain` and per-file log views.
- [ ] Frontend/admin UX: typed recovery request and reviewer flows, isolated execution-package
  transfer, status/expiry display, and safe error handling.
- [ ] Operations: move recovery private keys into offline/HSM custody, retain historical keys
  for old file wrappings, authenticate operators, and rehearse recovery. Rotation does not
  rewrap existing files, so every superseded private key must be kept.
- [ ] Operations: run `register_recovery_key.py` as part of environment provisioning. Without
  an active recovery key the API answers `No active recovery public key is configured` and no
  upload can succeed — staging hit exactly this after browser-side encryption landed.

### Admin and RBAC

- [x] Backend: explicit ADMIN and RECOVERY_OFFICER dependencies, bounded user/file views,
  account enable/disable commands, session revocation on disable, and audit events.
- [ ] Frontend: `AdminPage.vue` is three static cards plus a recovery-request count. Replace
  it with typed user, file, audit, and recovery views, and enforce the backend role policy in
  navigation and route guards rather than only checking for a token.

## P2 — Quality, Operations, and Hardening

### Testing and CI

- [ ] Add a CI workflow for backend format/lint/tests, OpenAPI method policy, migration drift,
  production SQL verification/parity, and frontend build/type/lint/test.
- [ ] Fail CI when the MySQL integration tests skip, rather than reporting green.
- [ ] Add real multi-connection MySQL tests for throttle locks, refresh replay, session limits,
  key-addition races, sharing/recovery races, and audit-chain serialization.
- [ ] Add failure-injection coverage for storage publish/cleanup, transaction rollback, invalid
  envelopes/signatures, optimistic revision conflicts, and recovery idempotency.
- [ ] Add frontend component and browser E2E tests for enrolment, login/refresh, unlock,
  upload/download, key rotation, share/revoke, recovery, and role denial. Unit coverage of the
  crypto modules already exists; the flows around them are untested.
- [ ] Run `upload.integration.test.ts` against a disposable backend in CI, so the live path is
  covered rather than skipped.
- [ ] Add coverage reporting with reviewed thresholds; skipped integration tests are not a
  release pass.

### Operations and Data Protection

- [x] `/health/live` and `/health/ready` exist; readiness checks database connectivity and the
  exact `0004_email_verification_codes` application schema marker without migrating.
- [x] TLS termination and the canonical-origin redirect are in place for staging.
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

- [ ] Write a normative account-envelope specification with locked vectors, matching
  `docs/crypto/FILE_ENVELOPE.md`. The AMK-wrap and private-key-bundle AADs live only in
  `account-crypto.ts`, and this project has already carried three mutually incompatible
  account-envelope AAD constructions.
- [x] The file-envelope AAD and its byte encodings are specified and locked by vectors.
- [ ] Extend the enrolment self-test to re-derive the public key from the decrypted private
  key, so a mismatched pair is caught before registration.
- [ ] Benchmark Argon2id parameters on supported clients and document minimum passphrase UX.
- [ ] Decide the fate of the plaintext PEM download offered at registration: either drop it in
  favour of passphrase unlock, or document it as an explicit, user-managed custody choice with
  its handling requirements.
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
- [x] The browser encrypts before upload against a normative, vector-locked envelope, and the
  ciphertext has been decrypted independently outside the TypeScript implementation.
- [x] A file uploaded through the browser can be downloaded and decrypted through the browser.
- [ ] Required MySQL 8.4 integration, concurrency, production-SQL, and parity tests pass in CI.
- [ ] The frontend implements the real cryptographic/API contracts without demo fallbacks and
  passes type, lint, unit, component, build, and browser E2E gates.
- [ ] Release operations, monitoring, backup/restore, offline recovery custody, and security
  review are documented and rehearsed.

## Explicitly Deferred Beyond the Current FYP Scope

Client-side file encryption/decryption, client-held private-key operations, and recipient DEK
rewrapping are **in the current scope**. Encryption and upload are implemented end to end;
decryption and rewrapping remain open at the browser boundary. The following stay deferred
unless scope changes:

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
