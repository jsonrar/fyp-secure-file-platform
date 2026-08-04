# Backend Architecture

## Decision

The backend is a **modular monolith**. This fits the FYP scope: one deployable FastAPI
application and one MySQL database, with strict internal boundaries. Microservices would
add distributed transactions and operational work without improving the security model.

The architecture is intentionally pragmatic. Add an abstraction when it protects a real
boundary (database, storage, cryptography, identity), not merely to add another directory.

Auth is the first completed database-backed vertical slice. File, sharing, audit-query,
recovery, and admin routers remain fail-closed with `501 feature_not_implemented` while
their use cases are still scaffolds.

## Dependency Direction

```text
HTTP router / dependency
          |
          v
Application service (one use-case transaction)
          |
          +----> repository / unit-of-work
          +----> storage port
          +----> crypto capability
          +----> domain policy
```

Rules:

1. Routers validate HTTP input, obtain the authenticated actor, call one application
   service, and map the result to a response schema. They contain no SQL, filesystem, or
   cryptographic logic.
2. Application services are use-case coordinators. They receive dependencies through
   constructors and never create database sessions or infrastructure adapters internally.
3. A command use case owns exactly one database transaction. Repositories may `flush`,
   but never `commit` independently.
   Abuse-control counters are a deliberate precondition exception: they commit separately
   so a rejected/rolled-back registration or login cannot erase its own throttle evidence.
   The protected domain mutation still owns one atomic transaction.
4. Capability services (crypto, hashing, watermarking, storage) do not import application
   services. This keeps the dependency graph acyclic.
5. ORM models are persistence models and never cross the API boundary. Pydantic schemas
   are transport models and never contain SQLAlchemy behavior.
6. Configuration and application composition happen at the process boundary
   (`core/config.py` and `main.py`). No module may depend on the current working directory.

## Package Responsibilities

```text
backend/app/
|-- api/                 FastAPI routers, dependencies, error/response mapping
|   `-- v1/              Versioned public API and its composition router
|-- core/                Configuration, database/session factory, security primitives
|-- domain/              Trusted contexts, immutable results, enums, public domain errors
|-- models/              SQLAlchemy persistence models
|-- repositories/        Persistence operations that never own transaction commits
|-- schemas/             Pydantic request/response DTOs
|-- services/            Application use cases and small capability services
|-- utils/               Pure, dependency-free helpers only
`-- main.py              Application factory and composition root

backend/migrations/      Alembic schema history (the schema source of truth)
backend/tests/
|-- unit/                Pure policy, crypto, validation, and service tests
|-- api/                 FastAPI contract and dependency-override tests
`-- integration/         MySQL, migration, repository, and storage tests
```

The Auth vertical slice introduced a concrete `AuthRepository`; SQLAlchemy's request-scoped
`Session` is its unit of work and `AuthService` is the transaction owner. Storage ports will
be introduced with the first storage-backed vertical slice. Empty generic base classes are
deliberately avoided.

## Identity and Authorization Boundary

The session model uses two independent, high-entropy opaque credentials rather than JWTs:

- The short-lived access token is a bearer credential. Only its SHA-256 hash is stored on
  the server-side session row. A single API dependency resolves it into a trusted
  `ActorContext` containing internal and public user/session IDs, role, status, and the
  validated access-token hash.
- A refresh token is stored as a separate hashed, generation-numbered record. It is
  single-use: a successful refresh consumes it and rotates both credentials. Reuse of an
  already consumed refresh token is treated as replay, revokes that entire session family,
  and appends an audit event. An absolute session expiry prevents indefinite refresh.
- Refresh rotation enforces a configurable minimum interval while holding the session lock,
  bounding how quickly one account can add token generations and global audit events.
- Logout revokes the current access/refresh family. Logout-all and password change revoke
  every active family for the account. Active-session limits evict the oldest sessions.

Passwords are normalized with Unicode NFC, must contain 15 to 128 characters, must not equal
the normalized username/email or email local part, and use `pwdlib`'s recommended Argon2id
hasher. Login uses `verify_and_update` so stored hashes can be upgraded when parameters
change; the verifier accepts legacy bcrypt records and replaces a successful one with
Argon2id. Unknown or malformed hashes fail as invalid credentials, while unknown users still
run one valid dummy-hash verification to reduce timing-based account enumeration. The
bundled common-password blocklist is intentionally small and local. It is a baseline for
this FYP, not a substitute for a maintained breached-password corpus in production.

Memory-hard password operations use a worker-shared bounded semaphore configured from the
worker's memory budget. Acquisition never waits in the shared synchronous thread pool: an
exhausted worker returns `429` with `Retry-After` and is not recorded as a password failure.
This capacity is independent from account/IP failure thresholds;
multi-worker deployments must multiply the per-process budget and still enforce concurrency
at the edge.

Login throttling is persisted in MySQL for normalized account and client-IP buckets;
registration has an IP bucket. Bucket identifiers are HMAC-SHA-256 values keyed by the
application secret, so usernames and IP addresses are not stored as plain throttle keys.
Account and IP thresholds are configured separately to avoid applying a small per-account
limit to an entire shared network. Login and password reauthentication inspect independent
failure buckets under sorted row locks before Argon2 runs; completed failures are recorded
after verification, while the separate worker capacity gate bounds in-flight work.
Registration rechecks its block after taking the same lock. This makes throttling consistent
across application workers, although proxy IP trust, retention/cleanup, and distributed
edge-level abuse protection remain deployment concerns.

Registration creates the user, RSA public key/fingerprint, and audit event in one
transaction. The matching private key is never persisted and is returned exactly once in a
non-cacheable TLS response. A lost registration response therefore requires a future
key-recovery/rotation workflow; the server cannot reproduce that private key.

Forgotten-password reset, email verification, MFA, and external identity federation are
not implemented. They require trusted out-of-band delivery, enrollment, or identity-provider
channels rather than additional unauthenticated database endpoints. `email_verified` is
currently reserved metadata and is not a login requirement.

Every non-public endpoint must require that context. Role checks happen at the API edge;
resource checks happen inside the use case using the actor ID. File access always requires
both:

1. an active logical access grant with the required capability; and
2. an active wrapped file key for the same user and file.

The default authorization result is deny. Admin, audit verification, and recovery routes
must declare explicit roles. Recovery uses maker-checker separation: a requester cannot
approve their own request.

## Transaction and Storage Boundary

MySQL transactions cannot atomically commit a local file. Upload therefore uses a staged
write and compensation:

1. validate size/type and stream plaintext through encryption to a random staging object;
2. calculate the encrypted hash and wrap the file key in memory;
3. begin one DB transaction for file metadata, owner grant, key wrappings, and audit log;
4. atomically rename the staged object to its final opaque object key;
5. commit the DB transaction;
6. on any failure, roll back and remove staged/final objects; a periodic orphan scan covers
   process crashes between rename and commit.

Database rows store an opaque storage object key, never a host filesystem path. Download
and encryption work must not block the async event loop; bounded blocking work runs in a
thread pool. Request size is rejected before reading an unbounded body.

## Cryptographic Boundary

- Each file gets an independent 256-bit AES key and 96-bit GCM nonce.
- Encrypted objects use a versioned envelope. Stable file identity, crypto version, and
  owner/file IDs are authenticated as AES-GCM associated data.
- AES keys exist only in memory long enough to wrap/unwrap and never enter API DTOs,
  application logs, exceptions, or database plaintext columns.
- RSA-OAEP uses SHA-256 and loaded keys are checked for type, minimum size, and fingerprint.
- The FYP's server-side decrypt flow may receive a user's private key transiently. Such
  endpoints must disable body logging and never persist the key. This is an explicit
  prototype limitation, not a production custody design.
- Recovery private-key operations are isolated from normal user endpoints and fully audited.

## Audit Integrity

An audit write is part of the same transaction as the security-sensitive action. Auth now
appends through a singleton `audit_chain_heads` row locked with `SELECT ... FOR UPDATE`;
the row records the last log and current hash so concurrent transactions cannot fork the
chain. The migration seeds genesis only for an empty audit table. Because revision `0001`
used a different canonical payload and lost datetime
microseconds, `0002` refuses to upgrade a non-empty legacy audit table; adopting one requires
a reviewed migration and external checkpoint. New timestamps retain six fractional digits
and absent metadata is stored canonically as `{}`, so rows can be recomputed from persisted
values. User references use restrictive foreign keys because cascading an ID update or hard
deletion would mutate hashed history; account deletion must therefore remain a status-based
soft delete. A plain database-resident hash chain detects accidental modification but cannot
stop a database administrator from rewriting and recomputing history; periodic signed/HMAC
checkpoints outside the audit database are still required for stronger tamper evidence.

## Schema and Delivery Rules

- ORM metadata plus Alembic migrations are the only schema authority.
- The application never calls `create_all()` and never runs destructive SQL on startup.
- A clean database must reach the current schema with `alembic upgrade head`.
- MySQL-specific integration tests use MySQL 8.4, not SQLite substitutes.
- Before merge: format check, lint, unit/API tests, migration upgrade, and migration drift
  checks must pass.

## Definition of Ready for a Use Case

A feature is ready to implement only when it has:

- request and response schemas with no secret/internal fields;
- authentication, role, and resource-policy requirements;
- one named transaction owner and rollback behavior;
- storage cleanup/compensation behavior where applicable;
- stable domain error codes and audit events;
- unit tests plus an API or integration test for the happy path and one denial path.
