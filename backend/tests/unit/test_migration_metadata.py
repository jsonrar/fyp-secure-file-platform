from __future__ import annotations

from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(*, output_buffer: StringIO | None = None) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"), output_buffer=output_buffer)
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def test_migration_history_is_a_single_ordered_chain() -> None:
    scripts = ScriptDirectory.from_config(_alembic_config())
    revisions = list(scripts.walk_revisions())

    assert scripts.get_heads() == ["0002_auth_identity_sessions"]
    assert [(revision.revision, revision.down_revision) for revision in revisions] == [
        ("0002_auth_identity_sessions", "0001_initial"),
        ("0001_initial", None),
    ]


def test_full_migration_chain_renders_as_mysql_sql() -> None:
    output = StringIO()

    command.upgrade(_alembic_config(output_buffer=output), "head", sql=True)

    rendered_sql = output.getvalue()
    guard_position = rendered_sql.index("auth_0002_audit_upgrade_guard")
    first_permanent_change_position = rendered_sql.index("ALTER TABLE users ADD COLUMN")
    assert guard_position < first_permanent_change_position
    assert "ck_auth_0002_requires_empty_audit_log" in rendered_sql
    assert "SELECT 0 FROM audit_logs LIMIT 1" in rendered_sql
    assert "CREATE TABLE users" in rendered_sql
    replacement_index_position = rendered_sql.index("CREATE INDEX idx_user_sessions_user_status")
    legacy_index_drop_position = rendered_sql.index("DROP INDEX idx_user_sessions_user_id")
    assert replacement_index_position < legacy_index_drop_position
    assert "UPDATE users SET user_uuid = UUID()" in rendered_sql
    assert "CREATE TABLE session_refresh_tokens" in rendered_sql
    assert "CREATE TABLE auth_login_throttles" in rendered_sql
    assert "UPDATE audit_logs SET metadata_json = JSON_OBJECT()" in rendered_sql
    assert "JSON_TYPE(metadata_json) = 'NULL'" in rendered_sql
    assert "MODIFY metadata_json JSON NOT NULL" in rendered_sql
    assert "CHANGE created_at created_at DATETIME(6)" in rendered_sql
    assert "ON DELETE RESTRICT ON UPDATE RESTRICT" in rendered_sql
    assert "CREATE TABLE audit_chain_heads" in rendered_sql
    assert "INSERT INTO audit_chain_heads" in rendered_sql
    assert "SELECT 1, id, current_hash FROM audit_logs" not in rendered_sql
    assert "0002_auth_identity_sessions" in rendered_sql


def test_auth_migration_downgrade_renders_as_mysql_sql() -> None:
    output = StringIO()

    command.downgrade(
        _alembic_config(output_buffer=output),
        "0002_auth_identity_sessions:0001_initial",
        sql=True,
    )

    rendered_sql = output.getvalue()
    guard_position = rendered_sql.index("SIGNAL SQLSTATE '45000'")
    first_schema_change_position = rendered_sql.index("DROP TABLE audit_chain_heads")
    assert guard_position < first_schema_change_position
    assert "0002_auth_identity_sessions is irreversible" in rendered_sql
    assert "DROP TABLE audit_chain_heads" in rendered_sql
    assert "ON DELETE SET NULL ON UPDATE CASCADE" in rendered_sql
    assert "DROP TABLE auth_login_throttles" in rendered_sql
    assert "DROP TABLE session_refresh_tokens" in rendered_sql
    assert "CHANGE access_token_hash session_token_hash" in rendered_sql
    assert "CHANGE access_expires_at expires_at" in rendered_sql
