from __future__ import annotations

from uuid import uuid4

import pytest
from scripts.deploy_mysql import deploy
from scripts.mysql_deployment import (
    DeploymentError,
    admin_url,
    application_url,
    connect_with_retry,
    inspect_database,
    migration_url,
    mysql_account,
)
from scripts.verify_mysql import verify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import settings

pytestmark = pytest.mark.integration
HEAD = "0002_auth_identity_sessions"


def _require_gate(evidence):
    if evidence is None:
        pytest.skip("Set MYSQL84_RELEASE_GATE=1 to run the MySQL 8.4 release gate")
    return evidence


def test_empty_database_deploys_directly_to_head(mysql_release_gate_bootstrap) -> None:
    evidence = _require_gate(mysql_release_gate_bootstrap)

    assert evidence.initial_tables == frozenset()
    assert evidence.first_head == HEAD
    assert evidence.verified_head == HEAD
    assert "alembic_version" in evidence.first_tables


def test_repeated_deployment_is_idempotent_and_preserves_data(
    mysql_release_gate_bootstrap,
) -> None:
    evidence = _require_gate(mysql_release_gate_bootstrap)

    assert evidence.repeated_head == HEAD
    assert evidence.repeated_verified_head == HEAD
    assert evidence.repeated_tables == evidence.first_tables
    assert evidence.repeated_sentinel_user_uuid == evidence.sentinel_user_uuid


def test_alembic_check_reports_no_schema_drift(mysql_release_gate_bootstrap) -> None:
    evidence = _require_gate(mysql_release_gate_bootstrap)

    assert evidence.verified_head == HEAD
    assert evidence.repeated_verified_head == HEAD


def test_real_0001_to_0002_upgrade_requires_backup_and_reaches_head(
    mysql_upgrade_target,
) -> None:
    with pytest.raises(DeploymentError, match="requires an upgrade; create and verify a backup"):
        deploy(wait_timeout=30.0, lock_timeout=30, confirm_backup=False)

    assert deploy(wait_timeout=60.0, lock_timeout=30, confirm_backup=True) == HEAD
    assert verify(wait_timeout=30.0, lock_timeout=30) == HEAD

    with connect_with_retry(
        migration_url(mysql_upgrade_target),
        30.0,
        connect_args=mysql_upgrade_target.DATABASE_CONNECT_ARGS,
    ) as connection:
        snapshot = inspect_database(connection, mysql_upgrade_target.DB_NAME)
        assert snapshot.revisions == (HEAD,)


def test_runtime_account_cannot_create_schema_objects(mysql_release_gate_bootstrap) -> None:
    _require_gate(mysql_release_gate_bootstrap)

    with connect_with_retry(
        application_url(settings),
        30.0,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        with pytest.raises(OperationalError) as error:
            connection.exec_driver_sql(
                "CREATE TABLE runtime_ddl_must_fail (id INTEGER NOT NULL PRIMARY KEY)"
            )
        assert error.value.orig.args[0] == 1142
        connection.rollback()


def test_migration_account_can_create_and_drop_schema_objects(
    mysql_release_gate_bootstrap,
) -> None:
    _require_gate(mysql_release_gate_bootstrap)

    with connect_with_retry(
        migration_url(settings),
        30.0,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        connection.exec_driver_sql(
            "CREATE TABLE migration_ddl_probe (id INTEGER NOT NULL PRIMARY KEY)"
        )
        connection.exec_driver_sql("DROP TABLE migration_ddl_probe")
        connection.commit()


def test_case_insensitive_unique_email_constraint(mysql_release_gate_bootstrap) -> None:
    _require_gate(mysql_release_gate_bootstrap)
    probe = uuid4().hex

    with connect_with_retry(
        application_url(settings),
        30.0,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        connection.execute(
            text(
                "INSERT INTO users (user_uuid, username, email, password_hash) "
                "VALUES (:user_uuid, :username, :email, :password_hash)"
            ),
            {
                "user_uuid": str(uuid4()),
                "username": f"unique-first-{probe}",
                "email": f"Unique-{probe}@Example.test",
                "password_hash": "not-a-real-password-hash",
            },
        )
        connection.commit()

        with pytest.raises(IntegrityError) as error:
            connection.execute(
                text(
                    "INSERT INTO users (user_uuid, username, email, password_hash) "
                    "VALUES (:user_uuid, :username, :email, :password_hash)"
                ),
                {
                    "user_uuid": str(uuid4()),
                    "username": f"unique-second-{probe}",
                    "email": f"unique-{probe}@example.TEST",
                    "password_hash": "not-a-real-password-hash",
                },
            )
        assert error.value.orig.args[0] == 1062
        connection.rollback()


def test_foreign_key_constraint_rejects_missing_user(mysql_release_gate_bootstrap) -> None:
    _require_gate(mysql_release_gate_bootstrap)

    with connect_with_retry(
        application_url(settings),
        30.0,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                text(
                    "INSERT INTO user_keys "
                    "(user_id, public_key_pem, algorithm, fingerprint) "
                    "VALUES (:user_id, :public_key_pem, :algorithm, :fingerprint)"
                ),
                {
                    "user_id": 18446744073709551614,
                    "public_key_pem": "integration-test-public-key",
                    "algorithm": "RSA-OAEP-SHA256",
                    "fingerprint": uuid4().hex * 2,
                },
            )
        assert error.value.orig.args[0] == 1452
        connection.rollback()


def test_delete_restrict_preserves_audit_history(mysql_release_gate_bootstrap) -> None:
    _require_gate(mysql_release_gate_bootstrap)
    probe = uuid4().hex

    with connect_with_retry(
        application_url(settings),
        30.0,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        result = connection.execute(
            text(
                "INSERT INTO users (user_uuid, username, email, password_hash) "
                "VALUES (:user_uuid, :username, :email, :password_hash)"
            ),
            {
                "user_uuid": str(uuid4()),
                "username": f"delete-restrict-{probe}",
                "email": f"delete-restrict-{probe}@example.test",
                "password_hash": "not-a-real-password-hash",
            },
        )
        user_id = int(result.lastrowid)
        connection.execute(
            text(
                "INSERT INTO audit_logs "
                "(actor_user_id, action, resource_type, result, metadata_json, current_hash) "
                "VALUES (:actor_user_id, :action, 'USER', 'SUCCESS', JSON_OBJECT(), :hash)"
            ),
            {
                "actor_user_id": user_id,
                "action": "release_gate_delete_restrict",
                "hash": uuid4().hex * 2,
            },
        )
        connection.commit()

        with pytest.raises(IntegrityError) as error:
            connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        assert error.value.orig.args[0] == 1451
        connection.rollback()


def test_runtime_and_migration_connections_use_verified_tls(
    mysql_release_gate_bootstrap,
) -> None:
    _require_gate(mysql_release_gate_bootstrap)

    assert settings.DATABASE_CONNECT_ARGS["ssl_verify_cert"] is True
    assert settings.DATABASE_CONNECT_ARGS["ssl_verify_identity"] is True
    for database_url in (application_url(settings), migration_url(settings)):
        with connect_with_retry(
            database_url,
            30.0,
            connect_args=settings.DATABASE_CONNECT_ARGS,
        ) as connection:
            cipher_row = connection.exec_driver_sql("SHOW SESSION STATUS LIKE 'Ssl_cipher'").one()
            version_row = connection.exec_driver_sql("SHOW SESSION STATUS LIKE 'Ssl_version'").one()
            assert str(cipher_row[1]).startswith("TLS_")
            assert str(version_row[1]) == "TLSv1.3"

    with connect_with_retry(
        admin_url(settings),
        30.0,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        assert int(connection.scalar(text("SELECT @@GLOBAL.require_secure_transport")) or 0) == 1
        for username, _, host in (mysql_account("DB"), mysql_account("MIGRATION_DB")):
            create_user = str(
                connection.exec_driver_sql("SHOW CREATE USER %s@%s", (username, host)).one()[-1]
            ).upper()
            assert " REQUIRE SSL" in create_user

    plain_engine = create_engine(
        application_url(settings),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5, "ssl_disabled": True},
    )
    try:
        with pytest.raises(OperationalError) as error, plain_engine.connect():
            pass
        # MySQL may report either secure-transport-required (3159) or deliberately
        # indistinguishable access-denied (1045) for an account that also has REQUIRE SSL.
        # The same credentials succeeded above with a verified TLS 1.3 connection.
        assert error.value.orig.args[0] in {1045, 3159}
    finally:
        plain_engine.dispose()
