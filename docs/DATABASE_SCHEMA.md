# Database Schema and Migration Policy

[English](DATABASE_SCHEMA.md) | [简体中文](DATABASE_SCHEMA.zh-CN.md)

## Source of Truth

SQLAlchemy metadata in `backend/app/models/` and the ordered Alembic revisions in
`backend/migrations/` are the development and CI schema-authoring authority.

Production does not run Alembic. The reviewed delivery artifacts under `database/mysql/`
are derived from that authoring history and are executed by a MySQL root/administrator:

1. `01-provision.sql` creates the database and the TLS-required `fyp_user` runtime account.
2. `02-schema.sql` installs the complete schema on an empty database, seeds the audit-chain
   singleton and compatibility marker, and grants exact table-level runtime privileges.
3. `03-verify.sql` reads server, account, grant, schema, marker, and singleton metadata before
   the application starts.

CI must compare the production schema artifact with the current Alembic head and ORM
metadata. A model or revision change is incomplete until the reviewed SQL artifact,
verification expectations, and parity tests change with it.

The current ordered history is:

1. `0001_initial_schema`: initial users, keys, sessions, files, access, integrity, audit,
   and recovery schema.
2. `0002_auth_identity_sessions`: public user/session UUIDs, access-session evolution,
   one-time refresh generations, persistent authentication throttles, password-change time,
   and the singleton audit-chain head.

The historical `docs/init.sql` development bootstrap has been deleted. A database previously
created from it is not automatically managed. The backend must not call
`Base.metadata.create_all()` at startup. `02-schema.sql` is the sole reviewed production
empty-database installer, not an application-startup hook.

## Development and CI Authoring Workflow

Run these commands from `backend/` only against disposable or explicitly Alembic-managed
development/CI databases:

```bash
alembic upgrade head
alembic current
alembic check
```

After intentionally changing an ORM model:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

Always review generated revisions. Autogenerate cannot understand data migrations,
application invariants, safe column backfills, or deployment order. A revision must be
forward-safe for existing data. Revision `0002_auth_identity_sessions` is intentionally
forward-only because its public UUIDs, session generations, throttle evidence, and password
hash upgrades cannot round-trip through `0001`; restore a backup for rollback, or rebuild a
disposable development database.

For a new staging or production database, follow [DEPLOYMENT.md](DEPLOYMENT.md): the same
root/administrator runs `01-provision.sql`, `02-schema.sql`, and the read-only
`03-verify.sql` in fail-fast batch mode. Only then does the application start as `fyp_user`.
There is no production `fyp_migrator`, no temporary switch of application `DB_*` credentials,
and no Python/Alembic command on the database server.

`02-schema.sql` deliberately refuses a non-empty schema and MySQL DDL is not fully
transactional. It must never be used as an upgrade mechanism. Future changes to a non-empty
production database require an immutable, versioned, reviewed DBA SQL upgrade with writer
drain, serialization, bounded waits, a verified restorable backup, explicit preconditions,
and release-specific post-verification.

The deleted Python runner previously supplied advisory locking, connectivity retries,
preflight/refusal checks, exact table validation, and backup confirmation. Release
orchestration and operator procedure must provide those controls around the root-executed SQL.

### Adopting a Legacy Development Database

A database created by the historical, now-deleted `docs/init.sql` has application tables but no
`alembic_version` row. For local development, do **not** run `alembic upgrade head` or blindly
stamp it as current:
the new baseline also renames `files.storage_path` to `storage_object_key` and removes the
ambiguous `file_access_grants.permission_level` column.

Migration `0002_auth_identity_sessions` contains safe backfills for a database that already
reached Alembic revision `0001_initial`; it does not adopt an unmanaged legacy schema and
does not make blind stamping safe. It also requires `audit_logs` to be empty: a non-empty
revision-0001 chain needs a reviewed adoption/checkpoint migration because its historical hash
payload and timestamp precision are not losslessly convertible.

- If the legacy development database is disposable and contains no needed data, recreate it
  and then use the normal development Alembic workflow.
- If a development database contains needed data, back it up and write/review a one-time
  adoption migration that performs those transformations before stamping the baseline.
- If any non-empty staging or production database needs to be retained, do not run Alembic or
  `02-schema.sql`; use a separately reviewed, versioned DBA SQL adoption/upgrade procedure.

Any such database remains legacy until it is deliberately recreated as disposable or handled
through a reviewed adoption procedure. No development migration command or production SQL in
this repository silently deletes, stamps, or adopts it.

## Table Groups

| Area | Tables | Purpose |
|---|---|---|
| Identity | `users`, `user_sessions`, `session_refresh_tokens`, `user_keys` | Accounts, opaque access sessions, one-time refresh generations, public-key history |
| Abuse control | `auth_login_throttles` | HMAC-keyed login, reauthentication, and registration buckets shared across workers |
| Files | `files`, `file_access_grants`, `file_key_wrappings` | Encrypted-object metadata plus logical and cryptographic access |
| Assurance | `integrity_checks`, `audit_logs`, `audit_chain_heads` | Verification history, security events, and serialized audit-chain append state |
| Recovery | `recovery_keys`, `recovery_requests` | Recovery public keys and maker-checker workflow |

The local encrypted object itself is not stored in MySQL. The `files` row stores an opaque
storage object key; the storage adapter resolves that key inside its configured root.

## Required Invariants

The following are transaction-level invariants and need integration tests even where MySQL
cannot express them cleanly:

1. Public user/session UUIDs are unique; numeric primary and foreign keys never enter API
   DTOs. Raw access and refresh credentials never enter database rows.
2. Each session has one current access hash and monotonically numbered refresh records.
   Refresh `(session_id, generation)` and token hashes are unique. A consumed token cannot
   be accepted again; replay revokes the complete session family.
3. Access expiry is not later than absolute session expiry. Refresh expiry is bounded by the
   same absolute expiry, and revoking a family makes all of its credentials unusable.
4. Authentication throttle keys are HMAC-SHA-256 values derived from secret, scope, and
   normalized identifier/IP. Plain usernames and IPs are not used as throttle primary keys.
5. Registration atomically creates the account, public key/fingerprint, and audit event;
   only the response receives the private RSA key.
6. Password change atomically replaces the Argon2id hash, records `password_changed_at`,
   revokes every active session family, and appends its audit event.
7. Creating a file atomically creates its metadata, owner grant, owner key wrapping,
   recovery wrapping (when enabled), and upload audit event.
8. Download requires both an active grant with download capability and an active user key
   wrapping for the same file and actor.
9. A `USER` key wrapping has `recipient_user_id` and `user_key_id`, but no
   `recovery_key_id`. A `RECOVERY` wrapping has only `recovery_key_id`.
10. Revocation changes the logical grant and all applicable key wrappings in one transaction.
11. Recovery transitions are conditional and monotonic:
   `PENDING -> APPROVED|REJECTED|CANCELLED`, then `APPROVED -> EXECUTED`.
   A requester cannot approve their own request.
12. Audit rows are append-only. Appending locks singleton `audit_chain_heads.id = 1` so
    concurrent transactions cannot create two entries with the same predecessor; the audit
    append commits or rolls back with its security-sensitive use case. Actor/target user
    foreign keys are restrictive because those IDs are hashed; referenced accounts use
    status-based soft deletion rather than a cascading hard delete.
13. Soft-deleted files are excluded from normal queries and cannot receive new grants.

The service layer owns these transactions. Repositories may query, add, and `flush`; they
must not independently commit.

## Time and Identifier Conventions

- API timestamps are timezone-aware UTC ISO-8601 values.
- MySQL `DATETIME` values are written/read as UTC; conversion happens at the API boundary.
- Public URLs use UUIDs/opaque identifiers, including account and session resources.
  Auto-increment IDs remain internal database keys.
- Storage object keys, raw session credentials, token hashes, key material, throttle HMACs,
  and filesystem roots must never appear in logs or public API schemas.

## Integration Test Database

The models use MySQL-specific `UNSIGNED`, `ENUM`, `VARBINARY`, JSON, collation, and referential
actions. Schema and repository integration tests therefore run against MySQL 8.4. SQLite is
not an acceptable behavioral substitute.

The minimum development migration test starts with an empty database, applies the ordered
revisions through `alembic upgrade head`, checks the current revision and expected tables,
and runs `alembic check` to detect metadata drift. A separate MySQL 8.4 production-path test
must run `01-provision.sql -> 02-schema.sql -> 03-verify.sql` against a disposable server,
inspect every verification result, and prove that the resulting schema matches the Alembic
head and ORM metadata. That test also checks the exact table-level grant matrix, absence of
the retired migrator identity and all elevated grant paths, the compatibility marker, and the
initial audit-chain singleton. Offline Alembic SQL remains a development/CI review aid, not a
production execution artifact. A legacy adoption test must begin from an explicit legacy
fixture rather than pretending it is revision `0001_initial`.
