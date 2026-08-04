from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401 - importing registers every ORM model
from app.core.database import Base
from app.domain.enums import SessionStatus


def test_all_models_are_registered_and_mappable() -> None:
    configure_mappers()

    assert len(Base.metadata.tables) == 13


def test_auth_models_expose_public_ids_and_rotation_history() -> None:
    users = Base.metadata.tables["users"]
    sessions = Base.metadata.tables["user_sessions"]
    refresh_tokens = Base.metadata.tables["session_refresh_tokens"]
    login_throttles = Base.metadata.tables["auth_login_throttles"]
    audit_logs = Base.metadata.tables["audit_logs"]
    audit_chain_heads = Base.metadata.tables["audit_chain_heads"]

    assert users.c.user_uuid.nullable is False
    assert users.c.password_changed_at.nullable is False
    assert sessions.c.session_uuid.nullable is False
    assert sessions.c.access_token_hash.nullable is False
    assert sessions.c.access_expires_at.nullable is False
    assert sessions.c.absolute_expires_at.nullable is False
    assert sessions.c.status.type.enum_class is SessionStatus
    session_foreign_key = next(iter(refresh_tokens.c.session_id.foreign_keys))
    assert session_foreign_key.target_fullname == "user_sessions.id"

    unique_names = {
        constraint.name
        for table in (users, sessions, refresh_tokens)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert {
        "uq_users_user_uuid",
        "uq_user_sessions_session_uuid",
        "uq_user_sessions_access_token_hash",
        "uq_session_refresh_tokens_token_hash",
        "uq_session_refresh_tokens_session_generation",
    } <= unique_names
    assert [column.name for column in login_throttles.primary_key] == ["scope", "key_hash"]
    assert audit_logs.c.metadata_json.nullable is False
    assert audit_logs.c.metadata_json.type.none_as_null is True
    audit_user_foreign_keys = {
        constraint.name: constraint for constraint in audit_logs.foreign_key_constraints
    }
    assert audit_user_foreign_keys["fk_audit_logs_actor_user"].ondelete == "RESTRICT"
    assert audit_user_foreign_keys["fk_audit_logs_actor_user"].onupdate == "RESTRICT"
    assert audit_user_foreign_keys["fk_audit_logs_target_user"].ondelete == "RESTRICT"
    assert audit_user_foreign_keys["fk_audit_logs_target_user"].onupdate == "RESTRICT"
    assert audit_logs.c.created_at.type.fsp == 6
    assert audit_chain_heads.c.id.autoincrement is False
    assert audit_chain_heads.c.updated_at.type.fsp == 6
