from __future__ import annotations

import hashlib
import math
import os
import re
import sys
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from alembic.config import Config
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

# Deployment-only variables live beside the normal application variables. Environment
# injection wins over the file so production secret stores remain authoritative.
load_dotenv(REPO_ROOT / ".env", override=False)

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if TYPE_CHECKING:
    from app.core.config import Settings

REQUIRED_MYSQL_MAJOR_MINOR = (8, 4)
REQUIRED_CHARACTER_SET = "utf8mb4"
REQUIRED_COLLATION = "utf8mb4_unicode_ci"

REVISION_TABLES: Mapping[str, frozenset[str]] = {
    "0001_initial": frozenset(
        {
            "audit_logs",
            "file_access_grants",
            "file_key_wrappings",
            "files",
            "integrity_checks",
            "recovery_keys",
            "recovery_requests",
            "user_keys",
            "user_sessions",
            "users",
        }
    ),
    "0002_auth_identity_sessions": frozenset(
        {
            "audit_chain_heads",
            "audit_logs",
            "auth_login_throttles",
            "file_access_grants",
            "file_key_wrappings",
            "files",
            "integrity_checks",
            "recovery_keys",
            "recovery_requests",
            "session_refresh_tokens",
            "user_keys",
            "user_sessions",
            "users",
        }
    ),
}


class DeploymentError(RuntimeError):
    """Raised when a database is unsafe or unsuitable for deployment."""


@dataclass(frozen=True)
class ServerInfo:
    version: str
    version_comment: str
    sql_mode: frozenset[str]
    time_zone: str = "+00:00"


@dataclass(frozen=True)
class DatabaseSnapshot:
    tables: frozenset[str]
    revisions: tuple[str, ...]
    character_set: str
    collation: str

    @property
    def application_tables(self) -> frozenset[str]:
        return self.tables - {"alembic_version"}


@dataclass(frozen=True)
class MigrationState:
    kind: str
    current_revision: str | None
    needs_backup: bool


def load_settings() -> Settings:
    try:
        # Import lazily so an invalid production environment is converted to a concise,
        # secret-safe CLI error instead of escaping during module initialization.
        from app.core.config import Settings as AppSettings

        return AppSettings()
    except ValidationError as exc:
        messages = "; ".join(
            str(error["msg"])
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            )
        )
        raise DeploymentError(f"invalid deployment settings: {messages}") from exc


def _required_environment(name: str) -> str:
    value = os.getenv(name, "")
    if not value.strip():
        raise DeploymentError(f"{name} must be set")
    if value != value.strip():
        raise DeploymentError(f"{name} must not have leading or trailing whitespace")
    return value


def _required_secret(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value:
        raise DeploymentError(f"{name} must be set")
    return value


def _optional_port(name: str, fallback: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return fallback
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise DeploymentError(f"{name} must be an integer") from exc
    if not 1 <= value <= 65535:
        raise DeploymentError(f"{name} must be between 1 and 65535")
    return value


def application_url(settings: Settings) -> URL:
    return settings.DATABASE_URL


def migration_url(settings: Settings) -> URL:
    username = os.getenv("MIGRATION_DB_USER", "")
    password = os.getenv("MIGRATION_DB_PASSWORD")

    if username and username != username.strip():
        raise DeploymentError("MIGRATION_DB_USER must not have leading or trailing whitespace")
    if bool(username) != bool(password):
        raise DeploymentError(
            "MIGRATION_DB_USER and MIGRATION_DB_PASSWORD must either both be set or both be absent"
        )
    if username and password:
        if username == settings.DB_USER:
            raise DeploymentError("MIGRATION_DB_USER must be distinct from DB_USER")
        return URL.create(
            drivername="mysql+pymysql",
            username=username,
            password=password,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            query={"charset": REQUIRED_CHARACTER_SET},
        )
    if settings.APP_ENV not in {"development", "test"}:
        raise DeploymentError(
            "non-development deployments require a separate MIGRATION_DB_USER and "
            "MIGRATION_DB_PASSWORD"
        )
    return settings.DATABASE_URL


def admin_url(settings: Settings) -> URL:
    return URL.create(
        drivername="mysql+pymysql",
        username=_required_environment("MYSQL_ADMIN_USER"),
        password=_required_secret("MYSQL_ADMIN_PASSWORD"),
        host=os.getenv("MYSQL_ADMIN_HOST", "").strip() or settings.DB_HOST,
        port=_optional_port("MYSQL_ADMIN_PORT", settings.DB_PORT),
        query={"charset": REQUIRED_CHARACTER_SET},
    )


def mysql_account(name_prefix: str) -> tuple[str, str, str]:
    if name_prefix == "DB":
        username = _required_environment("DB_USER")
        password = _required_secret("DB_PASSWORD")
        host_variable = "MYSQL_RUNTIME_USER_HOST"
    else:
        username = _required_environment(f"{name_prefix}_USER")
        password = _required_secret(f"{name_prefix}_PASSWORD")
        host_variable = "MYSQL_MIGRATION_USER_HOST"
    host = _required_environment(host_variable)

    if len(username) > 32 or any(ord(character) < 32 for character in username):
        raise DeploymentError(f"{name_prefix}_USER is not a valid MySQL account name")
    if len(host) > 255 or any(ord(character) < 32 for character in host):
        raise DeploymentError(f"{name_prefix}_HOST is not a valid MySQL account host")
    return username, password, host


def quote_identifier(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", identifier):
        raise DeploymentError(
            "MySQL database names must start with a letter or underscore and contain only "
            "letters, digits, and underscores"
        )
    if identifier.lower() in {"information_schema", "mysql", "performance_schema", "sys"}:
        raise DeploymentError("refusing to use a MySQL system schema for the application")
    return f"`{identifier}`"


def make_engine(
    url: URL,
    connect_args: Mapping[str, object] | None = None,
) -> Engine:
    connection_options = dict(connect_args or {})
    connection_options.setdefault("connect_timeout", 5)
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args=connection_options,
    )


@contextmanager
def connect_with_retry(
    url: URL,
    timeout_seconds: float,
    *,
    connect_args: Mapping[str, object] | None = None,
) -> Iterator[Connection]:
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise DeploymentError("connection timeout must be a finite value greater than zero")

    engine = make_engine(url, connect_args)
    deadline = time.monotonic() + timeout_seconds
    last_error: SQLAlchemyError | None = None

    try:
        while True:
            try:
                connection = engine.connect()
                break
            except SQLAlchemyError as exc:
                last_error = exc
                if time.monotonic() >= deadline:
                    raise DeploymentError(
                        f"could not connect to MySQL within {timeout_seconds:g} seconds"
                    ) from last_error
                time.sleep(min(1.0, max(0.05, deadline - time.monotonic())))

        try:
            yield connection
        finally:
            connection.close()
    finally:
        engine.dispose()


def inspect_server(connection: Connection) -> ServerInfo:
    row = connection.execute(
        text("SELECT VERSION(), @@version_comment, @@SESSION.sql_mode, @@SESSION.time_zone")
    ).one()
    version = str(row[0])
    version_comment = str(row[1])
    sql_mode = frozenset(part.strip().upper() for part in str(row[2]).split(",") if part)
    return ServerInfo(
        version=version,
        version_comment=version_comment,
        sql_mode=sql_mode,
        time_zone=str(row[3]),
    )


def validate_server(server: ServerInfo) -> None:
    if "mariadb" in f"{server.version} {server.version_comment}".lower():
        raise DeploymentError("MariaDB is not supported; deploy to MySQL 8.4")

    match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", server.version)
    if match is None:
        raise DeploymentError(f"could not parse MySQL server version {server.version!r}")
    major_minor = (int(match.group(1)), int(match.group(2)))
    if major_minor != REQUIRED_MYSQL_MAJOR_MINOR:
        raise DeploymentError(f"MySQL 8.4 is required; connected server reports {server.version!r}")
    if not ({"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"} & server.sql_mode):
        raise DeploymentError("MySQL strict SQL mode must be enabled for deployment")
    if server.time_zone not in {"+00:00", "UTC"}:
        raise DeploymentError(f"MySQL session time zone must be UTC; found {server.time_zone!r}")


def inspect_database(connection: Connection, database_name: str) -> DatabaseSnapshot:
    encoding_row = connection.execute(
        text(
            "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
            "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = :database_name"
        ),
        {"database_name": database_name},
    ).one_or_none()
    if encoding_row is None:
        raise DeploymentError(f"database {database_name!r} does not exist")

    tables = frozenset(
        str(row[0])
        for row in connection.execute(
            text(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = :database_name"
            ),
            {"database_name": database_name},
        )
    )
    revisions: tuple[str, ...] = ()
    if "alembic_version" in tables:
        revisions = tuple(
            sorted(
                str(row[0])
                for row in connection.execute(text("SELECT version_num FROM alembic_version"))
            )
        )

    return DatabaseSnapshot(
        tables=tables,
        revisions=revisions,
        character_set=str(encoding_row[0]).lower(),
        collation=str(encoding_row[1]).lower(),
    )


def validate_database_encoding(snapshot: DatabaseSnapshot) -> None:
    if snapshot.character_set != REQUIRED_CHARACTER_SET:
        raise DeploymentError(
            f"database character set must be {REQUIRED_CHARACTER_SET}; "
            f"found {snapshot.character_set}"
        )
    if snapshot.collation != REQUIRED_COLLATION:
        raise DeploymentError(
            f"database collation must be {REQUIRED_COLLATION}; found {snapshot.collation}"
        )


def migration_metadata() -> tuple[Config, frozenset[str], frozenset[str]]:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    scripts = ScriptDirectory.from_config(config)
    known_revisions = frozenset(revision.revision for revision in scripts.walk_revisions())
    heads = frozenset(scripts.get_heads())
    return config, known_revisions, heads


def classify_database(
    snapshot: DatabaseSnapshot,
    known_revisions: frozenset[str],
    heads: frozenset[str],
) -> MigrationState:
    if not snapshot.tables:
        return MigrationState(kind="empty", current_revision=None, needs_backup=False)
    if "alembic_version" not in snapshot.tables:
        raise DeploymentError(
            "refusing to migrate a non-empty database without alembic_version; "
            "follow the documented legacy adoption procedure"
        )
    if len(snapshot.revisions) != 1:
        raise DeploymentError("alembic_version must contain exactly one revision")

    current_revision = snapshot.revisions[0]
    if current_revision not in known_revisions:
        raise DeploymentError(f"database has unknown Alembic revision {current_revision!r}")
    expected_tables = REVISION_TABLES.get(current_revision)
    if expected_tables is None:
        raise DeploymentError(
            f"deployment table validation is not defined for revision {current_revision!r}"
        )

    missing = expected_tables - snapshot.application_tables
    unexpected = snapshot.application_tables - expected_tables
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing tables: {', '.join(sorted(missing))}")
        if unexpected:
            details.append(f"unexpected tables: {', '.join(sorted(unexpected))}")
        raise DeploymentError(
            f"database schema does not match revision {current_revision!r} ("
            + "; ".join(details)
            + ")"
        )

    if current_revision in heads:
        return MigrationState(kind="current", current_revision=current_revision, needs_backup=False)
    return MigrationState(kind="upgrade", current_revision=current_revision, needs_backup=True)


def validate_head(snapshot: DatabaseSnapshot, heads: frozenset[str]) -> str:
    if len(heads) != 1:
        raise DeploymentError("deployment requires a single Alembic head")
    state = classify_database(snapshot, frozenset(REVISION_TABLES), heads)
    head = next(iter(heads))
    if state.kind != "current" or state.current_revision != head:
        raise DeploymentError(f"database did not reach expected Alembic head {head!r}")
    return head


def validate_audit_chain_head(connection: Connection) -> None:
    row = connection.execute(
        text("SELECT COUNT(*), SUM(CASE WHEN id = 1 THEN 1 ELSE 0 END) FROM audit_chain_heads")
    ).one()
    if int(row[0]) != 1 or int(row[1] or 0) != 1:
        raise DeploymentError("audit_chain_heads must contain exactly the singleton row id = 1")


def deployment_lock_name(settings: Settings) -> str:
    # Advisory locks are already scoped to one MySQL server. Hash only the schema name so
    # two runners using different DNS aliases for the same server still serialize.
    digest = hashlib.sha256(settings.DB_NAME.encode()).hexdigest()[:40]
    return f"fyp-schema-{digest}"


def acquire_deployment_lock(
    connection: Connection,
    settings: Settings,
    timeout_seconds: int,
) -> str:
    if not 0 <= timeout_seconds <= 3600:
        raise DeploymentError("lock timeout must be between 0 and 3600 seconds")
    name = deployment_lock_name(settings)
    result = connection.scalar(
        text("SELECT GET_LOCK(:lock_name, :timeout_seconds)"),
        {"lock_name": name, "timeout_seconds": timeout_seconds},
    )
    connection.commit()
    if result != 1:
        raise DeploymentError(
            f"could not acquire the database deployment lock within {timeout_seconds} seconds"
        )
    return name


def release_deployment_lock(connection: Connection, lock_name: str) -> None:
    try:
        if connection.in_transaction():
            connection.commit()
        connection.execute(text("SELECT RELEASE_LOCK(:lock_name)"), {"lock_name": lock_name})
        connection.commit()
    except SQLAlchemyError:
        # Closing the connection also releases a MySQL advisory lock.
        with suppress(SQLAlchemyError):
            connection.invalidate()
