from __future__ import annotations

import os
import re
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from alembic import command
from scripts.deploy_mysql import deploy
from scripts.mysql_deployment import (
    admin_url,
    application_url,
    connect_with_retry,
    inspect_database,
    load_settings,
    migration_metadata,
    migration_url,
    mysql_account,
    quote_identifier,
)
from scripts.provision_mysql import provision
from scripts.verify_mysql import verify
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.core.config import settings

AUTH_TEST_DATABASE_URL_ENV = "AUTH_TEST_DATABASE_URL"
RELEASE_GATE_ENV = "MYSQL84_RELEASE_GATE"
RELEASE_GATE_CONFIRM_ENV = "MYSQL84_RELEASE_GATE_CONFIRM"
RELEASE_GATE_CONFIRMATION = "disposable-mysql-8.4-only"


@dataclass(frozen=True)
class MySQLReleaseGateEvidence:
    initial_tables: frozenset[str]
    first_head: str
    verified_head: str
    repeated_head: str
    repeated_verified_head: str
    first_tables: frozenset[str]
    repeated_tables: frozenset[str]
    sentinel_user_uuid: str
    repeated_sentinel_user_uuid: str


def _release_gate_enabled() -> bool:
    return os.getenv(RELEASE_GATE_ENV) == "1"


def _is_explicit_test_database(database_name: str) -> bool:
    return re.search(r"(?:^|_)test(?:$|_)", database_name.casefold()) is not None


def _assert_disposable_target() -> None:
    if os.getenv(RELEASE_GATE_CONFIRM_ENV) != RELEASE_GATE_CONFIRMATION:
        pytest.fail(f"{RELEASE_GATE_CONFIRM_ENV} must explicitly confirm a disposable MySQL target")

    current_settings = load_settings()
    if not _is_explicit_test_database(current_settings.DB_NAME):
        pytest.fail("MySQL release-gate database name must contain a distinct '_test' segment")
    for account in (mysql_account("DB"), mysql_account("MIGRATION_DB")):
        if not account[0].startswith("mcs21_gate_"):
            pytest.fail("MySQL release-gate account names must start with 'mcs21_gate_'")


def _drop_release_gate_target() -> None:
    _assert_disposable_target()
    current_settings = load_settings()
    database_identifier = quote_identifier(current_settings.DB_NAME)
    runtime_account = mysql_account("DB")
    migration_account = mysql_account("MIGRATION_DB")

    with connect_with_retry(
        admin_url(current_settings),
        30.0,
        connect_args=current_settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        connection.commit()
        autocommit_connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        autocommit_connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {database_identifier}")
        for username, _, host in (runtime_account, migration_account):
            autocommit_connection.exec_driver_sql(
                "DROP USER IF EXISTS %s@%s",
                (username, host),
            )


@pytest.fixture(scope="session", autouse=True)
def mysql_release_gate_bootstrap() -> Generator[MySQLReleaseGateEvidence | None, None, None]:
    if not _release_gate_enabled():
        yield None
        return

    _drop_release_gate_target()
    try:
        provision(wait_timeout=60.0, rotate_passwords=False)
        provision(wait_timeout=60.0, rotate_passwords=False)

        current_settings = load_settings()
        with connect_with_retry(
            migration_url(current_settings),
            30.0,
            connect_args=current_settings.DATABASE_CONNECT_ARGS,
        ) as connection:
            initial_snapshot = inspect_database(connection, current_settings.DB_NAME)

        first_head = deploy(wait_timeout=60.0, lock_timeout=30, confirm_backup=False)
        verified_head = verify(wait_timeout=30.0, lock_timeout=30)

        sentinel_user_uuid = "00000000-0000-4000-8000-000000000084"
        with connect_with_retry(
            application_url(current_settings),
            30.0,
            connect_args=current_settings.DATABASE_CONNECT_ARGS,
        ) as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(user_uuid, username, email, password_hash) "
                    "VALUES (:user_uuid, :username, :email, :password_hash)"
                ),
                {
                    "user_uuid": sentinel_user_uuid,
                    "username": "mysql84-release-gate-sentinel",
                    "email": "mysql84-release-gate@example.test",
                    "password_hash": "not-a-real-password-hash",
                },
            )
            connection.commit()
            first_snapshot = inspect_database(connection, current_settings.DB_NAME)

        repeated_head = deploy(wait_timeout=60.0, lock_timeout=30, confirm_backup=False)
        repeated_verified_head = verify(wait_timeout=30.0, lock_timeout=30)
        with connect_with_retry(
            application_url(current_settings),
            30.0,
            connect_args=current_settings.DATABASE_CONNECT_ARGS,
        ) as connection:
            repeated_snapshot = inspect_database(connection, current_settings.DB_NAME)
            repeated_sentinel_user_uuid = str(
                connection.scalar(
                    text("SELECT user_uuid FROM users WHERE username = :username"),
                    {"username": "mysql84-release-gate-sentinel"},
                )
            )

        yield MySQLReleaseGateEvidence(
            initial_tables=initial_snapshot.tables,
            first_head=first_head,
            verified_head=verified_head,
            repeated_head=repeated_head,
            repeated_verified_head=repeated_verified_head,
            first_tables=first_snapshot.tables,
            repeated_tables=repeated_snapshot.tables,
            sentinel_user_uuid=sentinel_user_uuid,
            repeated_sentinel_user_uuid=repeated_sentinel_user_uuid,
        )
    finally:
        _drop_release_gate_target()


@pytest.fixture
def mysql_upgrade_target(
    monkeypatch: pytest.MonkeyPatch,
    mysql_release_gate_bootstrap: MySQLReleaseGateEvidence | None,
) -> Generator[object, None, None]:
    if mysql_release_gate_bootstrap is None:
        pytest.skip("Set MYSQL84_RELEASE_GATE=1 to run the MySQL 8.4 release gate")

    required_values = {
        "DB_NAME": os.getenv("MYSQL84_UPGRADE_DB_NAME"),
        "DB_USER": os.getenv("MYSQL84_UPGRADE_RUNTIME_USER"),
        "DB_PASSWORD": os.getenv("MYSQL84_UPGRADE_RUNTIME_PASSWORD"),
        "MIGRATION_DB_USER": os.getenv("MYSQL84_UPGRADE_MIGRATION_USER"),
        "MIGRATION_DB_PASSWORD": os.getenv("MYSQL84_UPGRADE_MIGRATION_PASSWORD"),
    }
    missing = sorted(name for name, value in required_values.items() if not value)
    if missing:
        pytest.fail(f"Missing MySQL upgrade-gate settings: {', '.join(missing)}")
    for name, value in required_values.items():
        monkeypatch.setenv(name, str(value))

    _drop_release_gate_target()
    try:
        provision(wait_timeout=60.0, rotate_passwords=False)
        current_settings = load_settings()
        config, _, _ = migration_metadata()
        with connect_with_retry(
            migration_url(current_settings),
            30.0,
            connect_args=current_settings.DATABASE_CONNECT_ARGS,
        ) as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "0001_initial")
            snapshot = inspect_database(connection, current_settings.DB_NAME)
            assert snapshot.revisions == ("0001_initial",)
        yield current_settings
    finally:
        _drop_release_gate_target()


@pytest.fixture(scope="session")
def auth_mysql_url(
    mysql_release_gate_bootstrap: MySQLReleaseGateEvidence | None,
) -> URL:
    raw_url = os.getenv(AUTH_TEST_DATABASE_URL_ENV)
    if not raw_url:
        pytest.skip(
            f"Set {AUTH_TEST_DATABASE_URL_ENV} to run disposable MySQL auth integration tests"
        )

    database_url = make_url(raw_url)
    if not database_url.drivername.startswith("mysql"):
        pytest.fail(f"{AUTH_TEST_DATABASE_URL_ENV} must use a MySQL driver")
    if not database_url.database or not _is_explicit_test_database(database_url.database):
        pytest.fail(
            f"{AUTH_TEST_DATABASE_URL_ENV} database name must contain a distinct '_test' segment"
        )
    if _release_gate_enabled() and database_url.database != settings.DB_NAME:
        pytest.fail(f"{AUTH_TEST_DATABASE_URL_ENV} must target the release-gate database")
    return database_url


@pytest.fixture(scope="session")
def auth_mysql_engine(auth_mysql_url: URL) -> Generator[Engine, None, None]:
    engine = create_engine(
        auth_mysql_url,
        pool_pre_ping=True,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def auth_mysql_session(auth_mysql_engine: Engine) -> Generator[Session, None, None]:
    connection = auth_mysql_engine.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()


@pytest.fixture
def temporary_auth_mysql_connection(
    mysql_release_gate_bootstrap: MySQLReleaseGateEvidence | None,
) -> Generator[Connection, None, None]:
    """Use connection-local tables only; never mutate permanent application tables."""
    configured_url = os.getenv(AUTH_TEST_DATABASE_URL_ENV)
    database_url = make_url(configured_url) if configured_url else settings.DATABASE_URL
    engine = create_engine(
        database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    )
    connection: Connection | None = None
    try:
        try:
            connection = engine.connect()
            connection.exec_driver_sql(
                "CREATE TEMPORARY TABLE auth_test_privilege_probe (id INTEGER NOT NULL)"
            )
        except SQLAlchemyError as exc:
            if _release_gate_enabled():
                pytest.fail(
                    "MySQL release gate requires CREATE TEMPORARY TABLES on its disposable "
                    f"test identity ({type(exc).__name__})"
                )
            pytest.skip(
                "MySQL is unavailable or CREATE TEMPORARY TABLE is not permitted "
                f"({type(exc).__name__})"
            )
        yield connection
    finally:
        if connection is not None:
            connection.close()
        engine.dispose()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _release_gate_enabled() or exitstatus != pytest.ExitCode.OK:
        return
    terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    skipped = terminal_reporter.stats.get("skipped", []) if terminal_reporter else []
    if skipped:
        if terminal_reporter:
            terminal_reporter.write_sep(
                "=",
                f"MySQL release gate refuses {len(skipped)} skipped test(s)",
                red=True,
            )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
