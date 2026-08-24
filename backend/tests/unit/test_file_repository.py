from __future__ import annotations

from sqlalchemy.dialects import mysql

from app.repositories.file_repository import FileRepository


def _compiled_access_sql() -> str:
    statement = FileRepository._active_access_statement(user_id=7)
    return str(
        statement.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_authorized_access_admits_a_corrupted_file() -> None:
    """A damaged file must stay reachable to the people who hold a grant on it.

    Filtering CORRUPTED out of this statement removed the owner's only route to see the
    damage, re-check it, or delete it -- the row survived, but nothing could name it.
    """
    sql = _compiled_access_sql()

    assert "files.status IN ('ACTIVE', 'CORRUPTED')" in sql


def test_authorized_access_still_excludes_a_deleted_file() -> None:
    sql = _compiled_access_sql()

    assert "'DELETED'" not in sql


def test_authorized_access_still_requires_a_live_grant_and_wrapping() -> None:
    sql = _compiled_access_sql()

    assert "file_access_grants.status = 'ACTIVE'" in sql
    assert "file_key_wrappings.status = 'ACTIVE'" in sql
    assert "user_keys.status = 'ACTIVE'" in sql
