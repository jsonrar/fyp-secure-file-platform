from __future__ import annotations

from types import SimpleNamespace

import pytest
from scripts.mysql_deployment import (
    REQUIRED_COLLATION,
    REVISION_TABLES,
    DatabaseSnapshot,
    DeploymentError,
    ServerInfo,
    classify_database,
    connect_with_retry,
    deployment_lock_name,
    load_settings,
    migration_url,
    mysql_account,
    quote_identifier,
    validate_database_encoding,
    validate_server,
)
from scripts.provision_mysql import (
    MIGRATION_PRIVILEGES,
    RUNTIME_PRIVILEGES,
    _validate_grants,
)
from sqlalchemy.engine import URL

HEAD = "0002_auth_identity_sessions"
KNOWN_REVISIONS = frozenset(REVISION_TABLES)
HEADS = frozenset({HEAD})


def _snapshot(
    *,
    revision: str | None = None,
    application_tables: frozenset[str] = frozenset(),
    character_set: str = "utf8mb4",
    collation: str = REQUIRED_COLLATION,
) -> DatabaseSnapshot:
    tables = application_tables
    revisions: tuple[str, ...] = ()
    if revision is not None:
        tables |= {"alembic_version"}
        revisions = (revision,)
    return DatabaseSnapshot(
        tables=tables,
        revisions=revisions,
        character_set=character_set,
        collation=collation,
    )


def test_empty_database_is_safe_for_initial_migration() -> None:
    state = classify_database(_snapshot(), KNOWN_REVISIONS, HEADS)

    assert state.kind == "empty"
    assert state.current_revision is None
    assert state.needs_backup is False


def test_unmanaged_non_empty_database_is_rejected() -> None:
    with pytest.raises(DeploymentError, match="without alembic_version"):
        classify_database(
            _snapshot(application_tables=frozenset({"users"})),
            KNOWN_REVISIONS,
            HEADS,
        )


def test_managed_revision_requires_exact_expected_tables() -> None:
    expected = REVISION_TABLES["0001_initial"]
    state = classify_database(
        _snapshot(revision="0001_initial", application_tables=expected),
        KNOWN_REVISIONS,
        HEADS,
    )

    assert state.kind == "upgrade"
    assert state.current_revision == "0001_initial"
    assert state.needs_backup is True

    with pytest.raises(DeploymentError, match="missing tables: users"):
        classify_database(
            _snapshot(revision="0001_initial", application_tables=expected - {"users"}),
            KNOWN_REVISIONS,
            HEADS,
        )


def test_current_head_is_idempotent_and_does_not_require_backup() -> None:
    state = classify_database(
        _snapshot(revision=HEAD, application_tables=REVISION_TABLES[HEAD]),
        KNOWN_REVISIONS,
        HEADS,
    )

    assert state.kind == "current"
    assert state.current_revision == HEAD
    assert state.needs_backup is False


@pytest.mark.parametrize(
    ("server", "message"),
    [
        (ServerInfo("8.0.34", "MySQL Community Server", frozenset({"STRICT_TRANS_TABLES"})), "8.4"),
        (
            ServerInfo("8.4.1-MariaDB", "MariaDB Server", frozenset({"STRICT_TRANS_TABLES"})),
            "MariaDB",
        ),
        (ServerInfo("8.4.2", "MySQL Community Server", frozenset()), "strict SQL mode"),
        (
            ServerInfo(
                "8.4.2",
                "MySQL Community Server",
                frozenset({"STRICT_TRANS_TABLES"}),
                "SYSTEM",
            ),
            "time zone must be UTC",
        ),
    ],
)
def test_unsupported_mysql_server_configuration_is_rejected(
    server: ServerInfo,
    message: str,
) -> None:
    with pytest.raises(DeploymentError, match=message):
        validate_server(server)


def test_mysql_84_with_strict_mode_is_accepted() -> None:
    validate_server(
        ServerInfo(
            "8.4.3",
            "MySQL Community Server - GPL",
            frozenset({"STRICT_TRANS_TABLES", "NO_ENGINE_SUBSTITUTION"}),
        )
    )


def test_database_encoding_must_match_the_migration_metadata() -> None:
    with pytest.raises(DeploymentError, match="character set"):
        validate_database_encoding(_snapshot(character_set="latin1"))
    with pytest.raises(DeploymentError, match="collation"):
        validate_database_encoding(_snapshot(collation="utf8mb4_0900_ai_ci"))


def test_database_identifier_validation_prevents_sql_injection() -> None:
    assert quote_identifier("fyp_secure_file_platform") == "`fyp_secure_file_platform`"
    with pytest.raises(DeploymentError, match="database names"):
        quote_identifier("fyp`; DROP DATABASE production; --")
    with pytest.raises(DeploymentError, match="system schema"):
        quote_identifier("mysql")


def test_connection_wait_must_be_bounded() -> None:
    url = URL.create("mysql+pymysql", host="localhost", database="unused")

    with (
        pytest.raises(DeploymentError, match="finite value"),
        connect_with_retry(url, float("nan")),
    ):
        pytest.fail("an invalid timeout must fail before connecting")


def test_account_password_is_not_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_USER", "runtime")
    monkeypatch.setenv("DB_PASSWORD", " password with spaces ")
    monkeypatch.setenv("MYSQL_RUNTIME_USER_HOST", "10.%")

    assert mysql_account("DB") == ("runtime", " password with spaces ", "10.%")


def test_account_username_is_rejected_instead_of_trimmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_USER", " runtime ")
    monkeypatch.setenv("DB_PASSWORD", "password")
    monkeypatch.setenv("MYSQL_RUNTIME_USER_HOST", "10.%")

    with pytest.raises(DeploymentError, match="DB_USER must not have"):
        mysql_account("DB")


def test_invalid_settings_error_does_not_render_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_key = "secret-key-value-that-must-not-appear-in-errors"
    database_password = "database-password-that-must-not-appear-in-errors"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_DEBUG", "false")
    monkeypatch.setenv("SECRET_KEY", secret_key)
    monkeypatch.setenv("DB_PASSWORD", database_password)
    monkeypatch.setenv("DB_SSL_CA", "definitely-missing-deployment-ca.pem")

    with pytest.raises(DeploymentError, match="Database TLS files do not exist") as error:
        load_settings()

    assert secret_key not in str(error.value)
    assert database_password not in str(error.value)


def test_lock_name_is_stable_across_server_aliases() -> None:
    first = SimpleNamespace(DB_HOST="mysql-a", DB_PORT=3306, DB_NAME="fyp")
    second = SimpleNamespace(DB_HOST="mysql-b", DB_PORT=3307, DB_NAME="fyp")

    assert deployment_lock_name(first) == deployment_lock_name(second)  # type: ignore[arg-type]


def test_production_migrations_require_separate_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MIGRATION_DB_USER", raising=False)
    monkeypatch.delenv("MIGRATION_DB_PASSWORD", raising=False)
    settings = SimpleNamespace(
        APP_ENV="production",
        DB_HOST="mysql.example.test",
        DB_PORT=3306,
        DB_NAME="fyp",
        DB_USER="runtime",
        DATABASE_URL=URL.create(
            "mysql+pymysql",
            username="runtime",
            password="runtime-secret",
            host="mysql.example.test",
            database="fyp",
        ),
    )

    with pytest.raises(DeploymentError, match="separate MIGRATION_DB_USER"):
        migration_url(settings)  # type: ignore[arg-type]


def test_migration_credentials_are_kept_out_of_rendered_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIGRATION_DB_USER", "migrator")
    monkeypatch.setenv("MIGRATION_DB_PASSWORD", "secret:/@value")
    settings = SimpleNamespace(
        APP_ENV="production",
        DB_HOST="mysql.example.test",
        DB_PORT=3306,
        DB_NAME="fyp",
        DB_USER="runtime",
    )

    url = migration_url(settings)  # type: ignore[arg-type]

    assert url.username == "migrator"
    assert url.password == "secret:/@value"
    assert "secret" not in str(url)


def test_explicit_migration_username_must_differ_from_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIGRATION_DB_USER", "runtime")
    monkeypatch.setenv("MIGRATION_DB_PASSWORD", "migration-secret")
    settings = SimpleNamespace(
        APP_ENV="production",
        DB_HOST="mysql.example.test",
        DB_PORT=3306,
        DB_NAME="fyp",
        DB_USER="runtime",
    )

    with pytest.raises(DeploymentError, match="distinct from DB_USER"):
        migration_url(settings)  # type: ignore[arg-type]


def test_provisioned_runtime_and_migration_grants_are_schema_scoped() -> None:
    assert RUNTIME_PRIVILEGES == ("SELECT", "INSERT", "UPDATE", "DELETE")
    assert set(RUNTIME_PRIVILEGES) < set(MIGRATION_PRIVILEGES)
    assert "CREATE TEMPORARY TABLES" in MIGRATION_PRIVILEGES
    assert "ALL" not in MIGRATION_PRIVILEGES


class _GrantConnection:
    def __init__(self, statements: list[str]) -> None:
        self.statements = statements

    def exec_driver_sql(
        self,
        statement: str,
        parameters: tuple[str, str],
    ) -> list[tuple[str]]:
        assert statement == "SHOW GRANTS FOR %s@%s"
        assert parameters == ("runtime", "10.%")
        return [(grant,) for grant in self.statements]


def test_exact_runtime_grants_are_accepted() -> None:
    connection = _GrantConnection(
        [
            "GRANT USAGE ON *.* TO 'runtime'@'10.%' REQUIRE SSL",
            "GRANT SELECT, INSERT, UPDATE, DELETE ON `fyp`.* TO 'runtime'@'10.%'",
        ]
    )

    _validate_grants(  # type: ignore[arg-type]
        connection,
        "fyp",
        ("runtime", "secret", "10.%"),
        RUNTIME_PRIVILEGES,
    )


@pytest.mark.parametrize(
    ("grant", "message"),
    [
        (
            "GRANT ALL PRIVILEGES ON `fyp`.* TO 'runtime'@'10.%'",
            "unexpected schema privileges",
        ),
        ("GRANT SELECT ON *.* TO 'runtime'@'10.%'", "privileges outside"),
        ("GRANT 'admin'@'%' TO 'runtime'@'10.%'", "role or proxy grant"),
    ],
)
def test_excess_account_grants_are_rejected(grant: str, message: str) -> None:
    connection = _GrantConnection(
        [
            "GRANT USAGE ON *.* TO 'runtime'@'10.%' REQUIRE SSL",
            grant,
        ]
    )

    with pytest.raises(DeploymentError, match=message):
        _validate_grants(  # type: ignore[arg-type]
            connection,
            "fyp",
            ("runtime", "secret", "10.%"),
            RUNTIME_PRIVILEGES,
        )
