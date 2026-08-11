# MySQL Deployment

[English](DEPLOYMENT.md) | [Simplified Chinese](DEPLOYMENT.zh-CN.md)

These instructions target Oracle MySQL 8.4 and a new, empty application database. Production
database delivery consists entirely of three reviewed SQL files under `database/mysql/`.
A MySQL root/administrator executes them in fail-fast batch mode, in this order:

```text
01-provision.sql -> 02-schema.sql -> 03-verify.sql -> start as fyp_user
```

Production does not install or run Python/Alembic on the database server. SQLAlchemy metadata
and Alembic remain development/CI schema-authoring tools; `02-schema.sql` is the reviewed
empty-database production artifact derived from them.

## Identities and configuration

The release uses two identities:

- A MySQL root/administrator runs all three SQL files. Do not put this credential in the
  application `.env`, a command argument, or a release log.
- `fyp_user` runs the application only after verification. Inject its generated password
  through the standard application `DB_USER` and `DB_PASSWORD` settings.

The application connection also uses the existing settings:

- `DB_HOST`, `DB_PORT`, and `DB_NAME` (`fyp_secure_file_platform` for the supplied SQL)
- `DB_SSL_CA`, a readable CA bundle that verifies the server certificate and `DB_HOST`
- optionally, `DB_SSL_CERT` and `DB_SSL_KEY` together when mutual TLS is required

Verified TLS is mandatory outside development/test. Store database passwords and CA/client
files in the deployment secret store, not in Git or shell history. The normal production
settings also apply: set an appropriate `APP_ENV`, use `APP_DEBUG=false`, provide a
non-default `SECRET_KEY` of at least 32 characters, and configure explicit CORS origins.

No deployment-only administrator, migration, or account-host environment variables are used
or should be reintroduced. `MYSQL_ROOT_PASSWORD` and `MYSQL_PORT` in `.env.example` are
local-Compose settings only; production administrator credentials never enter the application
environment.

## Account-host scope

The tracked files deliberately use `fyp_user@localhost`. This safe default is directly usable
when the application connects from the database host. In a MySQL account, `localhost`
describes the client source; it is not the value of `DB_HOST`.

For a remote application connection, make protected deployment copies of all three SQL files
outside the repository. Replace every `localhost` account-host literal consistently in each
copy: the `CREATE USER` target in `01-provision.sql`, every table-level `GRANT` target in
`02-schema.sql`, and every expected account/grant value in `03-verify.sql`. Use the narrowest
host name or network pattern allowed by the deployment. Do not commit the environment-specific
copies, and do not use `%` unless an independently restricted private network and firewall
make that exposure acceptable. Verification must show exactly one intended runtime host row;
an old row at another host is a distinct MySQL identity and is a deployment failure.

## 1. Provision the database and runtime account

From the repository root, connect with an administrator that can create databases, users,
and grants. The final verification also needs permission to inspect MySQL grant metadata.
On the database server, run the file directly as a socket-authenticated root account:

```bash
sudo mysql < database/mysql/01-provision.sql
```

If MySQL root uses password authentication instead, keep the password out of the command;
the client prompts for it:

```bash
mysql --user=root --password < database/mysql/01-provision.sql
```

Do not add the mysql client's `--force` option. A SQL error must stop the batch instead of
continuing through partially satisfied deployment checks.

For a remote administrator connection, use the protected environment-specific copy, supply
the administrator password interactively, and verify TLS:

```bash
mysql --host=<mysql-host> --port=3306 --user=<administrator> --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/path/to/mysql-ca.pem \
  < /protected/path/01-provision.sql
```

The SQL creates `fyp_secure_file_platform` with `utf8mb4` and
`utf8mb4_unicode_ci`. It creates only `fyp_user`, requires SSL, asks MySQL to generate its
random password, and returns that cleartext password in the result set. Capture it immediately
into the secret store through a terminal/session that is not logged; it cannot be recovered
from MySQL later. Do not paste it into this repository, tickets, chat, or deployment logs.

`01-provision.sql` deliberately creates no application table and grants no table access.
`02-schema.sql` installs the exact runtime grants only after every application table exists.

The provisioning SQL is intentionally non-destructive:

- `CREATE USER IF NOT EXISTS` does not rotate an existing account's password. Retain the
  existing secret or perform a separately reviewed credential rotation.
- The later `GRANT` statements are additive. They do not revoke excess privileges or remove
  stale account-host rows.
- Existing matching accounts are not altered, including their password, authentication
  plugin, and TLS policy. Verification must show a nonempty TLS requirement; correct a
  missing requirement with a separately reviewed `ALTER USER` operation.

Review every warning and the verification output. If `fyp_user` already exists, confirm its
credential ownership, authentication plugin, nonempty password, TLS policy, host, and grants
before continuing. Correct unexpected state through a separately reviewed administrator
operation; never assume `CREATE USER IF NOT EXISTS` repaired it.

### Retire the former migrator identity

Production no longer uses `fyp_migrator`. On a server that previously used it:

1. Stop every old release job and remove the migrator credential from secret stores and job
   configuration.
2. Inventory every exact `fyp_migrator@host` account and confirm that no other owned workload
   depends on it.
3. Revoke/drop each confirmed obsolete account with a separately reviewed administrator
   change. Do not issue a wildcard or guessed `DROP USER` command.
4. Run `03-verify.sql`; any remaining account row, direct grant, role edge, default role, or
   proxy relationship for that name blocks deployment.

## 2. Install the empty-database schema

Run `02-schema.sql` as the same administrator, immediately after successful provisioning:

```bash
sudo mysql < database/mysql/02-schema.sql
# Or, when root uses password authentication:
mysql --user=root --password < database/mysql/02-schema.sql
```

For a remote administrator connection, use the matching protected copy and verified TLS:

```bash
mysql --host=<mysql-host> --port=3306 --user=<administrator> --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/path/to/mysql-ca.pem \
  < /protected/path/02-schema.sql
```

Never use the mysql client's `--force` option or an interactive `SOURCE` command. The file
checks MySQL 8.4, strict SQL mode, exact database encoding, and an empty persistent schema
before permanent DDL. It is deliberately non-idempotent and must run exactly once on a clean
database. It creates all 13 application tables, the `alembic_version` compatibility marker,
the audit-chain singleton, indexes, constraints, and these exact table-scoped grants:

- `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on the eleven ordinary state tables:
  `auth_login_throttles`, `recovery_keys`, `users`, `files`, `user_keys`, `user_sessions`,
  `file_access_grants`, `file_key_wrappings`, `integrity_checks`, `recovery_requests`, and
  `session_refresh_tokens`;
- `SELECT` and `INSERT` only on `audit_logs`;
- `SELECT` and `UPDATE` only on `audit_chain_heads`; and
- no runtime access to `alembic_version`, no schema/global/DDL privilege, no `GRANT OPTION`,
  and no role, proxy, column, or routine grant.

MySQL DDL is not fully transactional. If any statement fails, keep the application stopped
and do not rerun the file over the partial schema. Preserve evidence, diagnose the failure,
then recreate the disposable empty database or restore the verified pre-deployment backup
before restarting at `01-provision.sql`.

The former Python runner supplied connectivity retries, advisory locking, bounded waits,
backup confirmation, and failure wrapping. The SQL does not replace release orchestration:
use a single serialized release, an overall deadline, bounded connection/metadata-lock waits,
and a tested recovery procedure.

## 3. Verify as the administrator

Run the read-only verification after `02-schema.sql` completes and before the application
starts:

```bash
sudo mysql < database/mysql/03-verify.sql
# Or, when root uses password authentication:
mysql --user=root --password < database/mysql/03-verify.sql
```

For a remote deployment, use the matching protected verification copy and the same verified
TLS connection settings:

```bash
mysql --host=<mysql-host> --port=3306 --user=<administrator> --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/path/to/mysql-ca.pem \
  < /protected/path/03-verify.sql
```

Review every result set. Expected results are:

- the server is MySQL 8.4, strict SQL mode is enabled, the session time zone is the intended
  deployment value, and the application database uses `utf8mb4` with
  `utf8mb4_unicode_ci`;
- there is exactly one `fyp_user` row at the intended host, using
  `caching_sha2_password` with a nonempty hash, a nonempty SSL requirement, and no
  lock/expiry; `fyp_migrator` is absent at every host;
- neither name has a static or dynamic global privilege, schema privilege, column/routine
  grant, role/default-role edge, or proxy relationship, and server mandatory roles are empty;
- the table-grant symmetric difference is empty: exactly the eleven-table CRUD matrix plus
  audit-log `SELECT`/`INSERT` and chain-head `SELECT`/`UPDATE`, all non-grantable;
- the persistent table inventory, structural totals, critical foreign-key actions, check
  clauses, and composite indexes match `02-schema.sql`;
- `alembic_version` contains exactly the SQL artifact's compatibility marker
  `0002_auth_identity_sessions`; and
- `audit_chain_heads` contains exactly the genesis singleton: `id = 1`,
  `last_log_id IS NULL`, and a 64-zero current hash.

Because account creation and grants are additive, any extra row or privilege is a deployment
failure even if the expected grants are also present. Every query in `03-verify.sql` is a
`SELECT`; it diagnoses but does not repair state. Do not start the application until excess
access or schema drift has been corrected through a reviewed operation and verification has
been rerun successfully.

## 4. Start the application

Inject `fyp_user` and its captured password through `DB_USER` and `DB_PASSWORD`, retain the
normal host/name/TLS settings, and start the application only after verification succeeds.
Do not make the administrator credential available to the application process. No migrator
credential should exist in the release or application environment.

## Legacy and failed deployments

The former `docs/init.sql` was a historical development bootstrap and has been deleted. A
database previously created from it may contain application tables but no `alembic_version`;
it remains unmanaged. Follow the
[legacy adoption policy](DATABASE_SCHEMA.md#adopting-a-legacy-development-database).
`02-schema.sql` refuses that non-empty schema. Never run production Alembic, edit/stamp the
compatibility marker, or add `IF NOT EXISTS` clauses merely to bypass the refusal.

The three-file procedure is a fresh-database bootstrap, not an upgrade strategy. A future
release against a non-empty staging/production database requires a separate immutable,
versioned DBA SQL script derived from the reviewed schema change. Before that script runs,
drain writers, serialize the release, verify the current marker/schema, take and test a
restorable encrypted backup, and set bounded connection and metadata-lock waits. The matching
verification expectations must be updated for that release.

If schema installation or a future DBA upgrade fails, keep the application stopped and
preserve the database for diagnosis. MySQL DDL can commit incrementally, so recovery normally
means recreating the disposable empty database or restoring the verified backup. Do not run
`alembic downgrade`, manually edit `alembic_version`, or rerun `02-schema.sql` over partial or
existing state.

Store backups outside this repository, encrypt them, restrict access, and test restoration.
Database dumps contain account hashes, security audit evidence, encrypted-file metadata, and
wrapped keys.

## Container note

The root `docker-compose.yml` is a local MySQL convenience, not a production deployment
stack. On a fresh volume the image creates `DB_NAME` and grants its configured `DB_USER`
database access; that account can be broader than the production runtime grant. Existing
volumes retain their accounts and grants, so changing `.env` does not reprovision them and
the strict production verification may correctly report excess access.

Do not source the production provisioning file into an ordinary Compose development volume
unless deliberately adopting its account policy. It does not replace or otherwise alter an
existing Compose account, and cannot revoke the broader grant that the image may already
have assigned.

Do not mount the production SQL files or Alembic revisions under
`/docker-entrypoint-initdb.d`. Image initialization runs only for a fresh volume, generated
passwords must be captured securely, and existing deployments would silently miss later
release steps. Run `01`, `02`, and `03` explicitly as administrator-controlled operations.
