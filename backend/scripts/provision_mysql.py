from __future__ import annotations

import argparse
import re
import sys

from sqlalchemy import Connection
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

from scripts.mysql_deployment import (
    REQUIRED_CHARACTER_SET,
    REQUIRED_COLLATION,
    DeploymentError,
    admin_url,
    connect_with_retry,
    inspect_database,
    inspect_server,
    load_settings,
    migration_url,
    mysql_account,
    quote_identifier,
    validate_database_encoding,
    validate_server,
)

RUNTIME_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")
MIGRATION_PRIVILEGES = (
    *RUNTIME_PRIVILEGES,
    "CREATE",
    "DROP",
    "ALTER",
    "INDEX",
    "REFERENCES",
    "CREATE TEMPORARY TABLES",
)


def _create_or_update_account(
    connection: Connection,
    account: tuple[str, str, str],
    *,
    rotate_password: bool,
    require_ssl: bool,
) -> None:
    username, password, host = account
    ssl_clause = " REQUIRE SSL" if require_ssl else ""
    connection.exec_driver_sql(
        f"CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s{ssl_clause}",
        (username, host, password),
    )
    if rotate_password:
        connection.exec_driver_sql(
            "ALTER USER %s@%s IDENTIFIED BY %s",
            (username, host, password),
        )
    if require_ssl:
        _ensure_ssl_requirement(connection, account)


def _ensure_ssl_requirement(
    connection: Connection,
    account: tuple[str, str, str],
) -> None:
    username, _, host = account
    row = connection.exec_driver_sql("SHOW CREATE USER %s@%s", (username, host)).one()
    create_statement = str(row[-1]).upper()
    secure_requirements = (
        " REQUIRE SSL",
        " REQUIRE X509",
        " REQUIRE CIPHER",
        " REQUIRE ISSUER",
        " REQUIRE SUBJECT",
    )
    if not any(requirement in create_statement for requirement in secure_requirements):
        connection.exec_driver_sql("ALTER USER %s@%s REQUIRE SSL", (username, host))


def _grant(
    connection: Connection,
    database_identifier: str,
    account: tuple[str, str, str],
    privileges: tuple[str, ...],
) -> None:
    username, _, host = account
    sql = f"GRANT {', '.join(privileges)} ON {database_identifier}.* TO %s@%s"
    connection.exec_driver_sql(sql, (username, host))


def _validate_grants(
    connection: Connection,
    database_name: str,
    account: tuple[str, str, str],
    expected_privileges: tuple[str, ...],
) -> None:
    username, _, host = account
    rows = connection.exec_driver_sql("SHOW GRANTS FOR %s@%s", (username, host))
    expected = set(expected_privileges)
    discovered: set[str] = set()
    accepted_scopes = {f"`{database_name}`.*", f"{database_name}.*"}

    for row in rows:
        statement = str(row[0])
        match = re.match(r"^GRANT (.+?) ON (.+?) TO ", statement, flags=re.IGNORECASE)
        if match is None:
            raise DeploymentError(
                f"MySQL account {username!r}@{host!r} has an unexpected role or proxy grant"
            )
        privileges = {privilege.strip().upper() for privilege in match.group(1).split(",")}
        scope = match.group(2).strip()
        if " WITH GRANT OPTION" in statement.upper():
            raise DeploymentError(f"MySQL account {username!r}@{host!r} must not have GRANT OPTION")
        if scope == "*.*" and privileges == {"USAGE"}:
            continue
        if scope not in accepted_scopes:
            raise DeploymentError(
                f"MySQL account {username!r}@{host!r} has privileges outside {database_name!r}"
            )
        unexpected = privileges - expected
        if unexpected:
            raise DeploymentError(
                f"MySQL account {username!r}@{host!r} has unexpected schema privileges: "
                f"{', '.join(sorted(unexpected))}"
            )
        discovered.update(privileges)

    missing = expected - discovered
    if missing:
        raise DeploymentError(
            f"MySQL account {username!r}@{host!r} is missing schema privileges: "
            f"{', '.join(sorted(missing))}"
        )


def _account_url(base_url: URL, account: tuple[str, str, str], database_name: str) -> URL:
    username, password, _ = account
    return URL.create(
        drivername="mysql+pymysql",
        username=username,
        password=password,
        host=base_url.host,
        port=base_url.port,
        database=database_name,
        query={"charset": REQUIRED_CHARACTER_SET},
    )


def provision(*, wait_timeout: float, rotate_passwords: bool) -> None:
    settings = load_settings()
    database_identifier = quote_identifier(settings.DB_NAME)
    runtime_account = mysql_account("DB")
    migrator_account = mysql_account("MIGRATION_DB")
    if (runtime_account[0], runtime_account[2]) == (migrator_account[0], migrator_account[2]):
        raise DeploymentError("runtime and migration MySQL accounts must be distinct")

    target_admin_url = admin_url(settings)
    require_ssl = settings.APP_ENV not in {"development", "test"}
    with connect_with_retry(
        target_admin_url,
        wait_timeout,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        validate_server(inspect_server(connection))
        connection.commit()
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.exec_driver_sql(
            f"CREATE DATABASE IF NOT EXISTS {database_identifier} "
            f"CHARACTER SET {REQUIRED_CHARACTER_SET} COLLATE {REQUIRED_COLLATION}"
        )
        _create_or_update_account(
            connection,
            runtime_account,
            rotate_password=rotate_passwords,
            require_ssl=require_ssl,
        )
        _create_or_update_account(
            connection,
            migrator_account,
            rotate_password=rotate_passwords,
            require_ssl=require_ssl,
        )
        _grant(connection, database_identifier, runtime_account, RUNTIME_PRIVILEGES)
        _grant(connection, database_identifier, migrator_account, MIGRATION_PRIVILEGES)
        _validate_grants(connection, settings.DB_NAME, runtime_account, RUNTIME_PRIVILEGES)
        _validate_grants(connection, settings.DB_NAME, migrator_account, MIGRATION_PRIVILEGES)

    runtime_url = _account_url(settings.DATABASE_URL, runtime_account, settings.DB_NAME)
    with connect_with_retry(
        runtime_url,
        wait_timeout,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        validate_server(inspect_server(connection))
        validate_database_encoding(inspect_database(connection, settings.DB_NAME))

    # Reuse the same credential resolution as the migration runner so a typo cannot leave
    # provisioning apparently successful but deployment unable to connect.
    with connect_with_retry(
        migration_url(settings),
        wait_timeout,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        validate_server(inspect_server(connection))
        validate_database_encoding(inspect_database(connection, settings.DB_NAME))

    password_message = "rotated" if rotate_passwords else "left unchanged when already present"
    print(
        f"Provisioned MySQL database {settings.DB_NAME!r}; runtime and migration account "
        f"passwords were {password_message}."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Provision the MySQL database and least-privilege deployment accounts."
    )
    parser.add_argument("--wait-timeout", type=float, default=60.0)
    parser.add_argument(
        "--rotate-passwords",
        action="store_true",
        help="also replace passwords for accounts that already exist",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        provision(wait_timeout=args.wait_timeout, rotate_passwords=args.rotate_passwords)
    except DeploymentError as exc:
        print(f"MySQL provisioning failed: {exc}", file=sys.stderr)
        return 2
    except SQLAlchemyError:
        # Provisioning statements bind account passwords. Do not render the exception because
        # DBAPI parameter diagnostics could disclose those values.
        print(
            "MySQL provisioning failed: the server rejected an administrative operation; "
            "verify the admin credentials, account hosts, and privileges",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
