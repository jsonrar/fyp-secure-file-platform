from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Connection, Engine, func, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.auth import RequestContext
from app.domain.enums import SystemRole, UserStatus
from app.domain.errors import AuthenticationError
from app.models.audit_chain_head import AuditChainHead
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.user_key import UserKey
from app.models.user_session import UserSession
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import AuthService

pytestmark = pytest.mark.integration

TEMPORARY_AUTH_DDL = (
    """
    CREATE TEMPORARY TABLE users (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_uuid CHAR(36) NOT NULL UNIQUE,
        username VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE,
        email VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('USER', 'ADMIN', 'RECOVERY_OFFICER') NOT NULL DEFAULT 'USER',
        status ENUM('ACTIVE', 'DISABLED', 'DELETED') NOT NULL DEFAULT 'ACTIVE',
        email_verified BOOLEAN NOT NULL DEFAULT FALSE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        password_changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_login_at DATETIME NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TEMPORARY TABLE user_keys (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT UNSIGNED NOT NULL,
        public_key_pem TEXT NOT NULL,
        algorithm VARCHAR(50) NOT NULL,
        fingerprint CHAR(64) NOT NULL UNIQUE,
        status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        revoked_at DATETIME NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TEMPORARY TABLE user_sessions (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        session_uuid CHAR(36) NOT NULL UNIQUE,
        user_id BIGINT UNSIGNED NOT NULL,
        access_token_hash CHAR(64) NOT NULL UNIQUE,
        status ENUM('ACTIVE', 'EXPIRED', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
        ip_address VARCHAR(45) NULL,
        user_agent TEXT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        access_expires_at DATETIME NOT NULL,
        absolute_expires_at DATETIME NOT NULL,
        revoked_at DATETIME NULL,
        revoked_reason VARCHAR(100) NULL,
        INDEX idx_test_sessions_user_status (user_id, status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TEMPORARY TABLE session_refresh_tokens (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        session_id BIGINT UNSIGNED NOT NULL,
        token_hash CHAR(64) NOT NULL UNIQUE,
        generation INT UNSIGNED NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL,
        consumed_at DATETIME NULL,
        revoked_at DATETIME NULL,
        UNIQUE KEY uq_test_refresh_generation (session_id, generation)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TEMPORARY TABLE auth_login_throttles (
        scope ENUM('ACCOUNT', 'IP', 'REAUTH_ACCOUNT', 'REAUTH_IP', 'REGISTRATION_IP') NOT NULL,
        key_hash CHAR(64) NOT NULL,
        failed_count INT UNSIGNED NOT NULL DEFAULT 0,
        window_started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        blocked_until DATETIME NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (scope, key_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TEMPORARY TABLE audit_logs (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        actor_user_id BIGINT UNSIGNED NULL,
        action VARCHAR(100) NOT NULL,
        resource_type ENUM(
            'AUTH', 'USER', 'FILE', 'SHARE', 'RECOVERY', 'INTEGRITY', 'SYSTEM'
        ) NOT NULL,
        resource_id VARCHAR(100) NULL,
        target_user_id BIGINT UNSIGNED NULL,
        result ENUM('SUCCESS', 'FAIL') NOT NULL,
        ip_address VARCHAR(45) NULL,
        user_agent TEXT NULL,
        description TEXT NULL,
        metadata_json JSON NOT NULL,
        previous_hash CHAR(64) NULL,
        current_hash CHAR(64) NOT NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TEMPORARY TABLE audit_chain_heads (
        id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
        last_log_id BIGINT UNSIGNED NULL,
        current_hash CHAR(64) NOT NULL,
        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
)


def _create_temporary_auth_schema(connection: Connection) -> None:
    for statement in TEMPORARY_AUTH_DDL:
        connection.exec_driver_sql(statement)
    connection.exec_driver_sql(
        "INSERT INTO audit_chain_heads (id, last_log_id, current_hash) VALUES (1, NULL, %s)",
        ("0" * 64,),
    )
    connection.commit()


def _permanent_auth_row_counts(connection: Connection) -> dict[str, int] | None:
    """Inspect through another physical connection where temporary tables are invisible."""
    table_names = ("users", "user_keys", "user_sessions", "audit_logs")
    with connection.engine.connect() as verifier:
        verifier_inspector = inspect(verifier)
        if not all(verifier_inspector.has_table(table_name) for table_name in table_names):
            return None
        return {
            table_name: int(verifier.scalar(text(f"SELECT COUNT(*) FROM `{table_name}`")) or 0)
            for table_name in table_names
        }


def test_auth_database_is_migrated_to_expected_schema(auth_mysql_engine: Engine) -> None:
    inspector = inspect(auth_mysql_engine)
    table_names = set(inspector.get_table_names())

    assert {
        "alembic_version",
        "users",
        "user_keys",
        "user_sessions",
        "session_refresh_tokens",
        "auth_login_throttles",
        "audit_chain_heads",
        "audit_logs",
    } <= table_names

    with auth_mysql_engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))

    assert revision == "0002_auth_identity_sessions"
    assert {
        "session_uuid",
        "access_token_hash",
        "access_expires_at",
        "absolute_expires_at",
        "revoked_reason",
    } <= {column["name"] for column in inspector.get_columns("user_sessions")}


def test_mysql_collation_prevents_case_variant_duplicate_email(
    auth_mysql_session: Session,
) -> None:
    first = User(
        user_uuid=str(uuid4()),
        username=f"first-{uuid4().hex}",
        email="CaseSensitiveProbe@Example.com",
        password_hash="not-a-real-password-hash",
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=False,
    )
    second = User(
        user_uuid=str(uuid4()),
        username=f"second-{uuid4().hex}",
        email="casesensitiveprobe@example.COM",
        password_hash="not-a-real-password-hash",
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=False,
    )
    auth_mysql_session.add(first)
    auth_mysql_session.flush()
    auth_mysql_session.add(second)

    with pytest.raises(IntegrityError):
        auth_mysql_session.flush()

    auth_mysql_session.rollback()


def test_real_auth_flow_uses_only_connection_local_temporary_tables(
    temporary_auth_mysql_connection: Connection,
) -> None:
    permanent_counts_before = _permanent_auth_row_counts(temporary_auth_mysql_connection)
    _create_temporary_auth_schema(temporary_auth_mysql_connection)
    session = Session(bind=temporary_auth_mysql_connection, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        APP_DEBUG=False,
        SECRET_KEY="integration-test-secret-key-that-is-long-enough",
        USER_RSA_KEY_SIZE=2048,
    )
    fixed_now = datetime(2026, 8, 4, 4, 0, 0, 654321, tzinfo=UTC)
    current_time = [fixed_now]
    service = AuthService(db=session, settings=settings, clock=lambda: current_time[0])
    context = RequestContext(
        ip_address="203.0.113.20",
        user_agent="mysql-auth-integration-test",
    )
    original_password = "An original high entropy passphrase!"
    replacement_password = "A replacement high entropy passphrase!"

    try:
        registered = service.register(
            username="integration-user",
            email="integration-user@example.com",
            password=original_password,
            context=context,
        )
        assert registered.private_key_pem.startswith("-----BEGIN PRIVATE KEY-----")
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(UserKey)) == 1

        logged_in = service.login(
            username="integration-user",
            password=original_password,
            context=context,
        )
        original_actor = service.authenticate_access_token(logged_in.tokens.access_token)
        assert original_actor.user_public_id == registered.user.id

        # The baseline session-token timestamps use MySQL DATETIME(0), which may
        # round the inserted fractional second; one extra second crosses the bound.
        current_time[0] += timedelta(seconds=settings.AUTH_REFRESH_MIN_INTERVAL_SECONDS + 1)
        refreshed = service.refresh(
            refresh_token=logged_in.tokens.refresh_token,
            context=context,
        )
        with pytest.raises(AuthenticationError):
            service.authenticate_access_token(logged_in.tokens.access_token)
        refreshed_actor = service.authenticate_access_token(refreshed.tokens.access_token)
        assert refreshed_actor.session_public_id == original_actor.session_public_id

        revoked = service.change_password(
            actor=refreshed_actor,
            current_password=original_password,
            new_password=replacement_password,
            context=context,
        )
        assert revoked == 1
        with pytest.raises(AuthenticationError):
            service.authenticate_access_token(refreshed.tokens.access_token)

        stored_session = session.scalar(select(UserSession))
        assert stored_session is not None
        assert stored_session.status.value == "REVOKED"
        assert stored_session.revoked_reason == "password_changed"
        assert session.scalar(select(func.count()).select_from(AuditLog)) == 4

        # Force a database round trip: DATETIME without fsp=6 used to truncate
        # the hashed timestamp and made an otherwise intact chain unverifiable.
        session.expire_all()
        audit_logs = list(session.scalars(select(AuditLog).order_by(AuditLog.id)))
        expected_previous_hash = AuditLogService.GENESIS_HASH
        for audit_log in audit_logs:
            assert audit_log.created_at.microsecond == 654321
            assert audit_log.previous_hash == expected_previous_hash
            stored_content = service.audit.make_log_content(
                action=audit_log.action,
                actor_user_id=audit_log.actor_user_id,
                created_at=audit_log.created_at,
                description=audit_log.description,
                ip_address=audit_log.ip_address,
                metadata=audit_log.metadata_json,
                resource_id=audit_log.resource_id,
                resource_type=audit_log.resource_type,
                result=audit_log.result,
                target_user_id=audit_log.target_user_id,
                user_agent=audit_log.user_agent,
            )
            assert (
                service.audit.build_log_hash(expected_previous_hash, stored_content)
                == audit_log.current_hash
            )
            expected_previous_hash = audit_log.current_hash

        assert audit_logs[0].metadata_json == {}
        chain_head = session.get(AuditChainHead, 1)
        assert chain_head is not None
        assert chain_head.last_log_id == audit_logs[-1].id
        assert chain_head.current_hash == expected_previous_hash
    finally:
        session.close()

    permanent_counts_after = _permanent_auth_row_counts(temporary_auth_mysql_connection)
    assert permanent_counts_after == permanent_counts_before


def test_auth_migration_guards_fail_closed_without_permanent_writes(
    temporary_auth_mysql_connection: Connection,
) -> None:
    permanent_counts_before = _permanent_auth_row_counts(temporary_auth_mysql_connection)
    temporary_auth_mysql_connection.exec_driver_sql(
        "CREATE TEMPORARY TABLE audit_logs (id BIGINT PRIMARY KEY)"
    )
    temporary_auth_mysql_connection.exec_driver_sql("INSERT INTO audit_logs (id) VALUES (1)")
    temporary_auth_mysql_connection.exec_driver_sql(
        "CREATE TEMPORARY TABLE auth_0002_audit_upgrade_guard ("
        "empty_legacy_chain TINYINT NOT NULL, "
        "CONSTRAINT ck_auth_0002_requires_empty_audit_log "
        "CHECK (empty_legacy_chain = 1)"
        ") ENGINE=InnoDB"
    )

    with pytest.raises(DBAPIError) as upgrade_guard_error:
        temporary_auth_mysql_connection.exec_driver_sql(
            "INSERT INTO auth_0002_audit_upgrade_guard (empty_legacy_chain) "
            "SELECT 0 FROM audit_logs LIMIT 1"
        )
    assert upgrade_guard_error.value.orig.args[0] == 3819
    temporary_auth_mysql_connection.rollback()

    with pytest.raises(DBAPIError) as downgrade_guard_error:
        temporary_auth_mysql_connection.exec_driver_sql(
            "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = "
            "'0002_auth_identity_sessions is irreversible; restore a backup or rebuild'"
        )
    assert downgrade_guard_error.value.orig.args[0] == 1644
    temporary_auth_mysql_connection.rollback()

    permanent_counts_after = _permanent_auth_row_counts(temporary_auth_mysql_connection)
    assert permanent_counts_after == permanent_counts_before
