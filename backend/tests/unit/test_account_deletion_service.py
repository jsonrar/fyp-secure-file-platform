from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import SystemRole, UserStatus
from app.domain.errors import AuthenticationError, InvalidCurrentPasswordError
from app.services.account_deletion_service import AccountDeletionService

NOW = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def _actor() -> ActorContext:
    return ActorContext(
        user_id=7,
        user_public_id=USER_ID,
        session_id=8,
        session_public_id=UUID("55555555-5555-4555-8555-555555555555"),
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        access_token_hash="a" * 64,
    )


def _context() -> RequestContext:
    return RequestContext(ip_address="203.0.113.7", user_agent="pytest")


class FakeDb:
    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


class FakePasswords:
    def __init__(self, *, correct: str) -> None:
        self.correct = correct

    def verify(self, candidate: str, _hash: str) -> bool:
        return candidate == self.correct


class FakeAuthRepo:
    def __init__(self, user) -> None:
        self.user = user
        self.revoked_reason: str | None = None
        self.released: str | None = None

    def lock_user(self, _user_id: int):
        return self.user

    def revoke_all_session_families(self, _user_id: int, *, now, reason: str) -> int:
        self.revoked_reason = reason
        return 3

    def release_identifiers(self, user, *, tombstone: str) -> None:
        self.released = tombstone
        user.username = f"deleted-{tombstone}"
        user.email = f"deleted+{tombstone}@secureview.tech"


class FakeFileRepo:
    def __init__(self, files) -> None:
        self.files = files
        self.revoked: list[int] = []

    def lock_owned_files(self, _owner_id: int):
        return self.files

    def revoke_file_access_rows(self, file_pk: int, *, revoked_at) -> None:
        self.revoked.append(file_pk)


class FakeStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)


class FakeAudit:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def append(self, **values) -> None:
        self.entries.append(values)


def _file(pk: int, key: str):
    return SimpleNamespace(
        id=pk,
        storage_object_key=key,
        status="ACTIVE",
        deleted_at=None,
        updated_at=None,
        revision=1,
    )


def _service(*, password="correct-horse", files=None, user=None):
    user = user or SimpleNamespace(
        id=7,
        username="waldo",
        email="waldo@secureview.tech",
        password_hash="argon2-hash",
        status=UserStatus.ACTIVE,
    )
    db = FakeDb()
    auth_repo = FakeAuthRepo(user)
    file_repo = FakeFileRepo(files if files is not None else [])
    storage = FakeStorage()
    audit = FakeAudit()
    service = AccountDeletionService(
        db=db,
        passwords=FakePasswords(correct=password),
        storage=storage,
        auth_repository=auth_repo,
        file_repository=file_repo,
        audit_service=audit,
        clock=lambda: NOW,
    )
    return service, SimpleNamespace(
        db=db, auth=auth_repo, files=file_repo, storage=storage, audit=audit, user=user
    )


def test_deletes_the_owned_files_and_their_ciphertext() -> None:
    service, fakes = _service(files=[_file(1, "objects/a"), _file(2, "objects/b")])

    result = service.delete_account(
        actor=_actor(), password="correct-horse", context=_context()
    )

    assert result.files_deleted == 2
    assert [f.status for f in fakes.files.files] == ["DELETED", "DELETED"]
    assert fakes.storage.deleted == ["objects/a", "objects/b"]
    # A share handed to someone else must not outlive the account that granted it.
    assert fakes.files.revoked == [1, 2]


def test_ciphertext_is_removed_only_after_the_commit() -> None:
    # If the process dies between the two, rows marked DELETED with objects still present is
    # the recoverable state; live rows whose ciphertext is gone is not.
    service, fakes = _service(files=[_file(1, "objects/a")])
    order: list[str] = []
    fakes.db.commit = lambda: order.append("commit")  # type: ignore[method-assign]
    fakes.storage.delete_object = lambda key: order.append("unlink")  # type: ignore[method-assign]

    service.delete_account(actor=_actor(), password="correct-horse", context=_context())

    assert order == ["commit", "unlink"]


def test_closes_the_account_and_ends_every_session() -> None:
    service, fakes = _service()

    result = service.delete_account(
        actor=_actor(), password="correct-horse", context=_context()
    )

    assert fakes.user.status is UserStatus.DELETED
    assert result.sessions_revoked == 3
    assert fakes.auth.revoked_reason == "account_deleted"


def test_frees_the_username_and_email_for_a_new_account() -> None:
    # The whole point of closing the account is to be able to start over, and
    # identifier_exists does not filter by status -- so leaving these in place would reserve
    # them forever.
    service, fakes = _service()

    service.delete_account(actor=_actor(), password="correct-horse", context=_context())

    assert fakes.user.username != "waldo"
    assert fakes.user.email != "waldo@secureview.tech"
    # A reserved TLD would register fine and then break serialization wherever it is read back.
    assert fakes.user.email.endswith("@secureview.tech")


def test_a_wrong_password_deletes_nothing() -> None:
    # A live session on an unattended machine must not be enough for the one irreversible
    # action in the application.
    service, fakes = _service(files=[_file(1, "objects/a")])

    with pytest.raises(InvalidCurrentPasswordError):
        service.delete_account(actor=_actor(), password="not-it", context=_context())

    assert fakes.files.files[0].status == "ACTIVE"
    assert fakes.storage.deleted == []
    assert fakes.user.status is UserStatus.ACTIVE
    assert fakes.db.committed == 0
    assert fakes.db.rolled_back == 1


def test_an_already_closed_account_cannot_be_closed_again() -> None:
    closed = SimpleNamespace(
        id=7,
        username="deleted-abc",
        email="deleted+abc@secureview.tech",
        password_hash="argon2-hash",
        status=UserStatus.DELETED,
    )
    service, fakes = _service(user=closed)

    with pytest.raises(AuthenticationError):
        service.delete_account(actor=_actor(), password="correct-horse", context=_context())

    assert fakes.storage.deleted == []


def test_records_what_was_destroyed_against_the_real_username() -> None:
    # Written before the identifiers are released, or the history says "deleted-<uuid>" did it.
    service, fakes = _service(files=[_file(1, "objects/a")])

    service.delete_account(actor=_actor(), password="correct-horse", context=_context())

    entry = fakes.audit.entries[0]
    assert entry["action"] == "ACCOUNT_DELETED"
    assert entry["metadata"]["username"] == "waldo"
    assert entry["metadata"]["files_deleted"] == 1
