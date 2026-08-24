from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import SystemRole, UserStatus
from app.domain.errors import IntegrityVerificationError, StorageUnavailableError
from app.repositories.file_repository import FileAccessRecord
from app.services.file_storage_service import StorageObjectError, StorageObjectMissingError
from app.services.integrity_service import IntegrityService

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
FILE_ID = UUID("11111111-1111-4111-8111-111111111111")


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeRepository:
    def __init__(self) -> None:
        self.checks = []

    def add_integrity_check(self, check) -> None:
        self.checks.append(check)


class FakeAudit:
    def __init__(self) -> None:
        self.events = []

    def append(self, **event) -> None:
        self.events.append(event)


class FailingStorage:
    def __init__(self, failure: Exception) -> None:
        self.failure = failure

    def open_verified(self, object_key: str):
        raise self.failure

    def hash_object(self, object_key: str) -> tuple[str, int]:
        raise self.failure


def _actor() -> ActorContext:
    return ActorContext(
        user_id=7,
        user_public_id=UUID("22222222-2222-4222-8222-222222222222"),
        session_id=8,
        session_public_id=UUID("33333333-3333-4333-8333-333333333333"),
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        access_token_hash="a" * 64,
    )


def _record() -> FileAccessRecord:
    return FileAccessRecord(
        file=SimpleNamespace(
            id=91,
            file_uuid=str(FILE_ID),
            storage_object_key="opaque/object.ciphertext",
            encrypted_sha256="d" * 64,
            encrypted_size_bytes=5,
            status="ACTIVE",
            updated_at=NOW.replace(tzinfo=None),
            revision=1,
        ),
        grant=SimpleNamespace(),
        wrapping=SimpleNamespace(),
        user_key=SimpleNamespace(),
    )


@pytest.mark.parametrize(
    ("storage_failure", "public_error"),
    [
        (StorageObjectError("host path must stay private"), StorageUnavailableError),
        (StorageObjectMissingError("missing"), IntegrityVerificationError),
    ],
)
def test_download_integrity_failure_uses_stable_public_error(
    storage_failure: Exception,
    public_error: type[Exception],
) -> None:
    db = FakeDb()
    repository = FakeRepository()
    audit = FakeAudit()
    service = IntegrityService(
        db=db,
        settings=SimpleNamespace(),
        storage=FailingStorage(storage_failure),
        audit_service=audit,
        repository=repository,
        access_control=SimpleNamespace(),
        clock=lambda: NOW,
    )

    with pytest.raises(public_error):
        service.open_verified_for_download(
            record=_record(),
            actor=_actor(),
            context=RequestContext(),
        )

    assert db.commits == 1
    assert db.rollbacks == 0
    assert len(repository.checks) == 1
    assert audit.events[0]["action"] == "FILE_DOWNLOAD_INTEGRITY_FAILED"


class StubStorage:
    """Answers with a fixed digest and size, as a healthy or a damaged object would."""

    def __init__(self, *, sha256: str, size_bytes: int) -> None:
        self.sha256 = sha256
        self.size_bytes = size_bytes

    def hash_object(self, object_key: str) -> tuple[str, int]:
        return self.sha256, self.size_bytes

    def open_verified(self, object_key: str):
        return SimpleNamespace(
            sha256=self.sha256,
            size_bytes=self.size_bytes,
            stream=SimpleNamespace(close=lambda: None),
        )


def _service(storage, record) -> IntegrityService:
    return IntegrityService(
        db=FakeDb(),
        settings=SimpleNamespace(),
        storage=storage,
        audit_service=FakeAudit(),
        repository=FakeRepository(),
        access_control=SimpleNamespace(require=lambda **_: record),
        clock=lambda: NOW,
    )


def test_missing_object_does_not_mark_the_file_corrupted() -> None:
    """A momentary storage outage says nothing about bytes nobody could read.

    Marking the file here is what let an unmounted volume permanently strand an intact
    file: the status never moved back, and every read route filtered CORRUPTED away.
    """
    record = _record()
    service = _service(FailingStorage(StorageObjectMissingError("missing")), record)

    result = service.check(actor=_actor(), file_id=FILE_ID, context=RequestContext())

    assert result.status == "MISSING"
    assert record.file.status == "ACTIVE"
    assert record.file.revision == 1


def test_unreadable_object_does_not_mark_the_file_corrupted() -> None:
    record = _record()
    service = _service(FailingStorage(StorageObjectError("errno")), record)

    result = service.check(actor=_actor(), file_id=FILE_ID, context=RequestContext())

    assert result.status == "ERROR"
    assert record.file.status == "ACTIVE"


def test_modified_ciphertext_still_marks_the_file_corrupted() -> None:
    record = _record()
    service = _service(StubStorage(sha256="e" * 64, size_bytes=5), record)

    result = service.check(actor=_actor(), file_id=FILE_ID, context=RequestContext())

    assert result.status == "MODIFIED"
    assert record.file.status == "CORRUPTED"
    assert record.file.revision == 2
    assert record.file.updated_at == NOW.replace(tzinfo=None)


def test_a_passing_recheck_restores_a_corrupted_file() -> None:
    """Status describes the ciphertext now, not the worst ever observed about it."""
    record = _record()
    record.file.status = "CORRUPTED"
    service = _service(StubStorage(sha256="d" * 64, size_bytes=5), record)

    result = service.check(actor=_actor(), file_id=FILE_ID, context=RequestContext())

    assert result.status == "VALID"
    assert record.file.status == "ACTIVE"
    assert record.file.revision == 2


def test_a_passing_download_verification_restores_a_corrupted_file() -> None:
    record = _record()
    record.file.status = "CORRUPTED"
    service = _service(StubStorage(sha256="d" * 64, size_bytes=5), record)

    service.open_verified_for_download(
        record=record,
        actor=_actor(),
        context=RequestContext(),
    )

    assert record.file.status == "ACTIVE"


def test_a_valid_check_on_a_healthy_file_does_not_bump_the_revision() -> None:
    record = _record()
    service = _service(StubStorage(sha256="d" * 64, size_bytes=5), record)

    service.check(actor=_actor(), file_id=FILE_ID, context=RequestContext())

    assert record.file.status == "ACTIVE"
    assert record.file.revision == 1


def test_a_deleted_file_is_never_resurrected_by_a_verification() -> None:
    record = _record()
    record.file.status = "DELETED"
    service = _service(StubStorage(sha256="d" * 64, size_bytes=5), record)

    service.check(actor=_actor(), file_id=FILE_ID, context=RequestContext())

    assert record.file.status == "DELETED"
