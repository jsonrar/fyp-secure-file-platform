# MySQL Deployment

[English](DEPLOYMENT.md) | [简体中文](DEPLOYMENT.zh-CN.md)

These instructions deploy the database schema to MySQL 8.4. SQLAlchemy models and Alembic
revisions remain the only schema source of truth; the deployment scripts do not maintain a
second schema dump and never run `create_all()`.

Run all commands from `backend/` with the production Python dependencies installed:

```bash
python -m pip install -r requirements.txt
```

## Required configuration

Inject secrets through the deployment environment or a root `.env` that is excluded from
version control. Do not put passwords on command lines.

The application/runtime identity uses the existing settings:

- `DB_HOST`, `DB_PORT`, and `DB_NAME`
- `DB_USER` and `DB_PASSWORD`
- `DB_SSL_CA`, a readable CA bundle used to verify the server certificate and `DB_HOST`

`DB_SSL_CERT` and `DB_SSL_KEY` may also be set together when the server requires mutual TLS.
Verified TLS is mandatory outside development/test; each configured database/admin hostname
must be present in the server certificate. Store CA/client files as mounted deployment
secrets, not in Git.

The deployment runner uses a separate identity:

- `MIGRATION_DB_USER`
- `MIGRATION_DB_PASSWORD`

The normal non-development settings are also mandatory: `APP_ENV` must identify the target
environment, `APP_DEBUG=false`, `SECRET_KEY` must be a non-default value of at least 32
characters, and CORS origins must be explicit.

Database provisioning additionally requires these temporary administrative values:

- `MYSQL_ADMIN_USER` and `MYSQL_ADMIN_PASSWORD`
- `MYSQL_ADMIN_HOST` and `MYSQL_ADMIN_PORT` when different from `DB_HOST` and `DB_PORT`
- `MYSQL_RUNTIME_USER_HOST`, the MySQL account host pattern for the application
- `MYSQL_MIGRATION_USER_HOST`, the account host pattern for the deployment runner

Account host patterns are MySQL source-host restrictions, not the database server address.
Choose the narrowest values allowed by the deployment network. `%` is accepted by MySQL but
should only be used with an independently restricted private network and firewall.

## Account provisioning

Run this once for a new self-managed MySQL instance using an administrator that can create
databases, users, and grants. Grant validation also requires the administrator to inspect
other accounts' grants (normally `SELECT` on the MySQL system schema):

```bash
python -m scripts.provision_mysql
```

The command is safe to rerun when the two identities remain dedicated to this database. It
creates `DB_NAME` with `utf8mb4` and `utf8mb4_unicode_ci`, creates missing accounts, and
reapplies schema-scoped grants. It does not create application tables.

Existing account passwords are deliberately left unchanged. To perform an intentional
credential rotation after coordinating application rollout, use:

```bash
python -m scripts.provision_mysql --rotate-passwords
```

Outside development/test, both accounts are created with `REQUIRE SSL`. The runtime account
receives only `SELECT`, `INSERT`, `UPDATE`, and `DELETE`. The migration account additionally
receives `CREATE`, `DROP`, `ALTER`, `INDEX`, `REFERENCES`, and
`CREATE TEMPORARY TABLES` on this database. It receives no global privileges. Managed
database services may provision these identities through their own control plane instead;
the resulting grants and environment variables must be equivalent.

Provisioning fails closed when an existing identity has global, role, proxy, grant-option,
other-database, table-specific, or excess schema privileges. Use new dedicated identities or
review and remove the excess grants administratively; the script never revokes an unrelated
account's access automatically.

The runtime identity is restricted at the database/DDL boundary, not per table: its DML grant
also covers audit and migration metadata tables. If the threat model includes theft of the
runtime database credential, introduce reviewed table-specific identities or stored routines
and externally anchor audit checkpoints before treating the audit chain as independently
tamper-resistant.

Remove `MYSQL_ADMIN_PASSWORD` from the deployment environment as soon as provisioning is
complete. Neither the migration nor verification command needs administrative credentials.

## Release sequence

1. Confirm the target is MySQL 8.4, strict SQL mode is enabled, and the application is not
   writing while a schema upgrade is in progress.
2. For a database already managed by Alembic and behind the repository head, create and
   verify a restorable backup. MySQL DDL is not fully transactional.
3. Run the migration before starting the new application version.
4. Verify the schema using the runtime identity.

For a new, empty database:

```bash
python -m scripts.deploy_mysql
python -m scripts.verify_mysql
```

For an existing Alembic-managed database that needs an upgrade:

```bash
python -m scripts.deploy_mysql --confirm-backup
python -m scripts.verify_mysql
```

`--confirm-backup` records an operator assertion; it does not create the backup. Store backups
outside this repository, encrypt them, restrict access, and test restoration. Database dumps
contain account hashes, security audit evidence, encrypted-file metadata, and wrapped keys.

The migration runner waits for connectivity, validates the server and database encoding,
sets and verifies a UTC session time zone, and acquires a database-specific MySQL advisory
lock. It permits only a completely empty database or an exact schema for a known Alembic
revision. After `alembic upgrade head`, it checks the revision, the expected table set, the
singleton audit-chain head, and Alembic metadata drift. A second run at head is idempotent and
does not require backup confirmation.

Both commands accept bounded wait options when an orchestrator needs different timings:

```bash
python -m scripts.deploy_mysql --wait-timeout 120 --lock-timeout 120
python -m scripts.verify_mysql --wait-timeout 60 --lock-timeout 60
```

## Legacy and failed deployments

A non-empty database without `alembic_version` is unmanaged. The runner stops without
upgrading, stamping, dropping, or resetting it. Follow the
[legacy adoption policy](DATABASE_SCHEMA.md#adopting-a-legacy-development-database); never
use `alembic stamp` merely to bypass the guard.

Revision `0002_auth_identity_sessions` also refuses a revision-`0001` database whose audit
chain already contains rows. That history needs a reviewed adoption/checkpoint migration.

If a migration fails, keep the application stopped and preserve the database for diagnosis.
Because the current `0002` data transformation is intentionally forward-only and MySQL DDL
can commit incrementally, rollback means restoring the verified pre-deployment backup. Do not
run `alembic downgrade`, manually edit `alembic_version`, or rerun provisioning with password
rotation as a recovery technique.

## Container note

The root `docker-compose.yml` is a local MySQL service, not a production deployment stack.
Do not mount migrations under `/docker-entrypoint-initdb.d`: official image initialization
runs only for a fresh data volume, so existing deployments would silently miss later schema
revisions. Run the guarded migration command as an explicit release job instead.
