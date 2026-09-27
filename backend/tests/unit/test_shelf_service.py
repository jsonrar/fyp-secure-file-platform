from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import app.models  # noqa: F401 -- registers every model with Base.metadata
from app.core.database import Base
from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import SystemRole, UserStatus
from app.domain.errors import (
    FileResourceNotFoundError,
    ShelfNameUnavailableError,
    ShelfNotFoundError,
)
from app.models.audit_chain_head import AuditChainHead
from app.models.file import File
from app.models.user import User
from app.schemas.shelf_schema import ShelfCreate
from app.services.audit_log_service import AuditLogService
from app.services.shelf_service import ShelfService

CONTEXT = RequestContext(ip_address="203.0.113.9", user_agent="pytest")


@pytest.fixture
def session() -> Session:
    """An in-memory SQLite stand-in for the parts of the schema shelves touch.

    SQLite is enough here because nothing under test depends on MySQL behaviour: the
    interesting rules are ownership, the unique name per owner, and the fact that deleting a
    shelf detaches its files instead of removing them. Foreign keys are switched on
    explicitly, because SQLite ignores them by default and `ON DELETE SET NULL` is exactly
    what this suite is about.
    """
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record) -> None:  # pragma: no cover - driver hook
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    tables = [
        Base.metadata.tables[name]
        for name in ("users", "shelves", "files", "audit_logs", "audit_chain_heads")
    ]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine, expire_on_commit=False) as active:
        active.add(AuditChainHead(id=1, last_log_id=None, current_hash="0" * 64))
        active.commit()
        yield active
    engine.dispose()


def _user(session: Session, username: str) -> User:
    user = User(
        user_uuid=str(uuid4()),
        username=username,
        email=f"{username}@example.invalid",
        password_hash="not-a-real-hash",
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    session.add(user)
    session.commit()
    return user


def _actor(user: User) -> ActorContext:
    return ActorContext(
        user_id=user.id,
        user_public_id=UUID(str(user.user_uuid)),
        session_id=1,
        session_public_id=uuid4(),
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        access_token_hash="a" * 64,
    )


def _file(session: Session, owner: User, name: str) -> File:
    file_id = uuid4()
    record = File(
        file_uuid=str(file_id),
        owner_id=owner.id,
        original_filename=name,
        stored_filename=f"{file_id}.ciphertext",
        storage_object_key=f"{file_id}/{uuid4()}.ciphertext",
        mime_type="application/pdf",
        file_size_bytes=10,
        encrypted_size_bytes=10,
        encryption_algorithm="AES-256-GCM",
        iv=b"n" * 12,
        auth_tag=b"t" * 16,
        encrypted_sha256="a" * 64,
        status="ACTIVE",
    )
    session.add(record)
    session.commit()
    return record


def _service(session: Session) -> ShelfService:
    return ShelfService(db=session, audit_service=AuditLogService(session))


def test_a_shelf_name_is_unique_per_owner_not_globally(session: Session) -> None:
    alice, bob = _user(session, "alice"), _user(session, "bob")
    service = _service(session)

    service.create(actor=_actor(alice), name="Coursework", context=CONTEXT)
    # The same name in another account is an ordinary coincidence, not a conflict.
    service.create(actor=_actor(bob), name="Coursework", context=CONTEXT)

    with pytest.raises(ShelfNameUnavailableError):
        service.create(actor=_actor(alice), name="Coursework", context=CONTEXT)

    assert [shelf.name for shelf in service.list_shelves(actor=_actor(alice)).shelves] == [
        "Coursework"
    ]


def test_a_name_that_differs_only_in_whitespace_is_the_same_name() -> None:
    """Otherwise one account ends up with two shelves it cannot tell apart."""
    assert ShelfCreate(name="  Tax   Returns  ").name == "Tax Returns"

    with pytest.raises(ValidationError):
        ShelfCreate(name="   ")


def test_only_the_owner_can_see_rename_or_delete_a_shelf(session: Session) -> None:
    alice, bob = _user(session, "alice"), _user(session, "bob")
    service = _service(session)
    shelf = service.create(actor=_actor(alice), name="Private", context=CONTEXT)

    assert service.list_shelves(actor=_actor(bob)).shelves == []
    with pytest.raises(ShelfNotFoundError):
        service.rename(
            actor=_actor(bob),
            shelf_id=shelf.shelf_id,
            name="Renamed by a stranger",
            context=CONTEXT,
        )
    with pytest.raises(ShelfNotFoundError):
        service.delete(actor=_actor(bob), shelf_id=shelf.shelf_id, context=CONTEXT)
    with pytest.raises(ShelfNotFoundError):
        service.resolve_owned_shelf_pk(owner_id=bob.id, shelf_id=shelf.shelf_id)


def test_moving_a_file_changes_only_where_it_is_filed(session: Session) -> None:
    alice = _user(session, "alice")
    actor = _actor(alice)
    service = _service(session)
    shelf = service.create(actor=actor, name="Coursework", context=CONTEXT)
    record = _file(session, alice, "report.pdf")
    before = {
        "storage_object_key": record.storage_object_key,
        "encrypted_sha256": record.encrypted_sha256,
        "iv": record.iv,
        "auth_tag": record.auth_tag,
        "encryption_algorithm": record.encryption_algorithm,
        "status": record.status,
        "owner_id": record.owner_id,
        "file_uuid": record.file_uuid,
    }

    assert service.move_file(
        actor=actor,
        file_id=UUID(record.file_uuid),
        shelf_id=shelf.shelf_id,
        context=CONTEXT,
    ) == shelf.shelf_id

    session.refresh(record)
    assert record.shelf_id is not None
    # Nothing about the envelope, the ciphertext, or the file's identity may move with it.
    assert {key: getattr(record, key) for key in before} == before

    assert (
        service.move_file(
            actor=actor,
            file_id=UUID(record.file_uuid),
            shelf_id=None,
            context=CONTEXT,
        )
        is None
    )
    session.refresh(record)
    assert record.shelf_id is None


def test_a_file_cannot_be_moved_by_a_non_owner_or_onto_someone_elses_shelf(
    session: Session,
) -> None:
    alice, bob = _user(session, "alice"), _user(session, "bob")
    service = _service(session)
    alice_shelf = service.create(actor=_actor(alice), name="Alice", context=CONTEXT)
    record = _file(session, alice, "report.pdf")

    # Bob may hold a share for this file, but reorganising it would rearrange Alice's
    # library from outside her account.
    with pytest.raises(FileResourceNotFoundError):
        service.move_file(
            actor=_actor(bob),
            file_id=UUID(record.file_uuid),
            shelf_id=None,
            context=CONTEXT,
        )

    with pytest.raises(ShelfNotFoundError):
        service.move_file(
            actor=_actor(alice),
            file_id=UUID(record.file_uuid),
            shelf_id=uuid4(),
            context=CONTEXT,
        )
    # Alice's own shelf still works, so the refusal above was about ownership.
    assert service.move_file(
        actor=_actor(alice),
        file_id=UUID(record.file_uuid),
        shelf_id=alice_shelf.shelf_id,
        context=CONTEXT,
    ) == alice_shelf.shelf_id


def test_deleting_a_shelf_returns_its_files_to_the_root_and_deletes_none_of_them(
    session: Session,
) -> None:
    alice = _user(session, "alice")
    actor = _actor(alice)
    service = _service(session)
    shelf = service.create(actor=actor, name="Coursework", context=CONTEXT)
    first, second = _file(session, alice, "a.pdf"), _file(session, alice, "b.pdf")
    for record in (first, second):
        service.move_file(
            actor=actor,
            file_id=UUID(record.file_uuid),
            shelf_id=shelf.shelf_id,
            context=CONTEXT,
        )

    result = service.delete(actor=actor, shelf_id=shelf.shelf_id, context=CONTEXT)

    assert result.shelf_id == shelf.shelf_id
    assert result.files_returned_to_root == 2
    assert service.list_shelves(actor=actor).shelves == []
    for record in (first, second):
        session.refresh(record)
        assert record.status == "ACTIVE"
        assert record.shelf_id is None
