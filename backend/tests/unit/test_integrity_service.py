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
