"""Prove the runtime application account cannot do what only an administrator may.

`database/mysql/02-schema.sql` grants the runtime identity ('fyp_user'@'localhost')
table-scoped SELECT/INSERT/UPDATE/DELETE only -- never DDL, never GRANT, never
unrestricted UPDATE on the append-only audit tables. `tests/unit/test_mysql_sql_deployment.py`
already checks that the SQL file says this; it never connects to a live server. This
script is the live counterpart: it applies the exact GRANT statements from that file
(renamed to the disposable release-gate database) against a running MySQL instance,
then connects AS the runtime account and asserts the boundary actually holds there --
that CRUD works on a granted table, and DDL/GRANT/unrestricted-audit-UPDATE fail --
and separately that the administrator connection (which applied the grants) is not
subject to the same restriction.

Reads connection details from environment variables, mirroring verify_mysql_tls.py:

    DB_HOST, DB_PORT, DB_NAME
    ADMIN_DB_USER, ADMIN_DB_PASSWORD           -- can run DDL/GRANT (e.g. root)
    RUNTIME_DB_USER, RUNTIME_DB_PASSWORD       -- the account being tested

Never logs a password. Exits non-zero on the first unexpected grant behaviour.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SQL_PATH = REPO_ROOT / "database" / "mysql" / "02-schema.sql"
PRODUCTION_DATABASE_NAME = "fyp_secure_file_platform"
PRODUCTION_RUNTIME_USER = "fyp_user"
PRODUCTION_RUNTIME_HOST = "localhost"

GRANT_STATEMENT_RE = re.compile(
    r"^GRANT\s+.+?\s+ON\s+`fyp_secure_file_platform`\.`[a-z0-9_]+`\s+"
    r"TO\s+'fyp_user'@'localhost';",
    re.MULTILINE | re.DOTALL,
)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(
            f"check_runtime_grants: missing required environment variable {name}", file=sys.stderr
        )
        sys.exit(2)
    return value


def _extract_runtime_grants(database_name: str, runtime_user: str, runtime_host: str) -> list[str]:
    schema_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    statements = GRANT_STATEMENT_RE.findall(schema_sql)
    if not statements:
        raise RuntimeError(f"no runtime GRANT statements found in {SCHEMA_SQL_PATH}")
    rewritten = []
    for statement in statements:
        statement = statement.replace(f"`{PRODUCTION_DATABASE_NAME}`", f"`{database_name}`")
        statement = statement.replace(
            f"'{PRODUCTION_RUNTIME_USER}'@'{PRODUCTION_RUNTIME_HOST}'",
            f"'{runtime_user}'@'{runtime_host}'",
        )
        rewritten.append(statement)
    return rewritten


def _connect(
    host: str, port: int, user: str, password: str, database: str
) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=host, port=port, user=user, password=password, database=database, connect_timeout=10
    )


def _expect_denied(cursor: pymysql.cursors.Cursor, sql: str, label: str) -> None:
    try:
        cursor.execute(sql)
    except pymysql.err.OperationalError as exc:
        # 1142/1143/1044/1227: command/column/table/grant access denied for user.
        if exc.args and exc.args[0] in (1142, 1143, 1044, 1227):
            return
        raise AssertionError(
            f"{label}: unexpected error {exc!r}, wanted an access-denied error"
        ) from exc
    else:
        raise AssertionError(f"{label}: statement unexpectedly succeeded: {sql}")


def main() -> int:
    host = _required_env("DB_HOST")
    port = int(os.environ.get("DB_PORT", "3306"))
    database = _required_env("DB_NAME")
    admin_user = _required_env("ADMIN_DB_USER")
    admin_password = _required_env("ADMIN_DB_PASSWORD")
    runtime_user = _required_env("RUNTIME_DB_USER")
    runtime_password = _required_env("RUNTIME_DB_PASSWORD")
    runtime_host = os.environ.get("RUNTIME_DB_HOST", "%")

    admin_connection = _connect(host, port, admin_user, admin_password, database)
    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                (runtime_user, runtime_host, runtime_password),
            )
            for statement in _extract_runtime_grants(database, runtime_user, runtime_host):
                cursor.execute(statement)
        admin_connection.commit()

        # The administrator connection itself must still be able to do DDL --
        # otherwise this whole test would be meaningless.
        with admin_connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS _grant_probe (id INT PRIMARY KEY)")
            cursor.execute("DROP TABLE _grant_probe")
        admin_connection.commit()
    finally:
        admin_connection.close()

    runtime_connection = _connect(host, port, runtime_user, runtime_password, database)
    try:
        with runtime_connection.cursor() as cursor:
            # CRUD on a table the runtime identity is meant to own.
            cursor.execute(
                "INSERT INTO users (user_uuid, username, email, password_hash, role, status, "
                "email_verified) VALUES (%s, %s, %s, %s, 'USER', 'ACTIVE', 0)",
                (
                    "00000000-0000-4000-8000-000000000001",
                    "grant-probe-user",
                    "grant-probe@example.invalid",
                    "not-a-real-hash",
                ),
            )
            runtime_connection.commit()

            _expect_denied(cursor, "CREATE TABLE runtime_should_not_ddl (id INT)", "CREATE TABLE")
            _expect_denied(cursor, "DROP TABLE users", "DROP TABLE")
            _expect_denied(
                cursor,
                f"GRANT SELECT ON `{database}`.`users` TO '{runtime_user}'@'{runtime_host}'",
                "GRANT",
            )
            # audit_logs is append-only for the runtime identity: SELECT, INSERT only.
            _expect_denied(cursor, "DELETE FROM audit_logs", "DELETE FROM audit_logs")
            _expect_denied(
                cursor,
                "UPDATE audit_logs SET description = 'tampered' WHERE id = 1",
                "UPDATE audit_logs (full row)",
            )
            # audit_chain_heads may only have its three named columns updated.
            _expect_denied(
                cursor,
                "UPDATE audit_chain_heads SET schema_revision = 'tampered' WHERE id = 1",
                "UPDATE audit_chain_heads.schema_revision",
            )
            # Leave no trace so a repeat run of this script against the same
            # disposable database stays idempotent.
            cursor.execute(
                "DELETE FROM users WHERE user_uuid = %s",
                ("00000000-0000-4000-8000-000000000001",),
            )
        runtime_connection.commit()
    finally:
        runtime_connection.close()

    print(
        f"check_runtime_grants: {runtime_user!r} is confined to CRUD and cannot perform "
        "DDL, GRANT, or the writes the release-gate schema reserves to the administrator"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"check_runtime_grants: FAILED -- {exc}", file=sys.stderr)
        sys.exit(1)
