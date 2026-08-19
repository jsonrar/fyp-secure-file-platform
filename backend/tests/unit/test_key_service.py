from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import SystemRole, UserStatus
from app.domain.errors import KeyBundleInvalidError, KeyBundleRevisionConflictError
from app.domain.keys import (
    ClientKeyAddition,
    EncryptedPrivateKeyBundleInput,
    KeyProtectionProfileInput,
)
from app.services.key_service import KeyService

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
PROFILE_ID = UUID("11111111-1111-4111-8111-111111111111")
CURRENT_KEY_ID = UUID("22222222-2222-4222-8222-222222222222")
NEW_KEY_ID = UUID("33333333-3333-4333-8333-333333333333")
BUNDLE_ID = UUID("44444444-4444-4444-8444-444444444444")


def _pem(key: rsa.RSAPrivateKey) -> str:
    return (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )


def _actor() -> ActorContext:
    return ActorContext(
        user_id=7,
        user_public_id=UUID("55555555-5555-4555-8555-555555555555"),
        session_id=8,
        session_public_id=UUID("66666666-6666-4666-8666-666666666666"),
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        access_token_hash="a" * 64,
    )


def _addition(new_public_key_pem: str) -> ClientKeyAddition:
    ciphertext = b"client-encrypted-pkcs8" * 20
    return ClientKeyAddition(
        authorizing_key_id=CURRENT_KEY_ID,
        protection_profile_id=PROFILE_ID,
        expected_profile_revision=3,
        key_id=NEW_KEY_ID,
        public_key_pem=new_public_key_pem,
        algorithm="RSA-OAEP-SHA256",
        key_size_bits=2048,
        private_key_bundle=EncryptedPrivateKeyBundleInput(
            bundle_id=BUNDLE_ID,
            format_version=1,
            private_key_format="PKCS8-DER",
            derivation_algorithm="HKDF-SHA256",
            derivation_salt=b"d" * 16,
            encryption_algorithm="AES-256-GCM",
            encrypted_private_key=ciphertext,
            nonce=b"n" * 12,
            auth_tag=b"t" * 16,
            aad_version=1,
            ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(),
        ),
    )


def _protection() -> KeyProtectionProfileInput:
    return KeyProtectionProfileInput(
        profile_id=PROFILE_ID,
        format_version=1,
        kdf_algorithm="ARGON2ID",
        kdf_version=19,
        kdf_salt=b"s" * 16,
        kdf_memory_kib=65_536,
        kdf_iterations=3,
        kdf_parallelism=1,
        derived_key_length=32,
        amk_wrapping_algorithm="AES-256-GCM",
        wrapped_amk=b"w" * 32,
        amk_nonce=b"n" * 12,
        amk_auth_tag=b"t" * 16,
        aad_version=1,
    )


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeRepository:
    def __init__(self, current_public_key_pem: str) -> None:
        self.profile = SimpleNamespace(
            profile_uuid=str(PROFILE_ID),
            format_version=1,
            revision=3,
        )
        self.current_key = SimpleNamespace(
            id=10,
            key_uuid=str(CURRENT_KEY_ID),
            public_key_pem=current_public_key_pem,
        )
        self.keys = []
        self.bundles = []

    def lock_protection_profile(self, user_id: int):
        assert user_id == 7
        return self.profile

    def lock_current_client_key(self, user_id: int):
        assert user_id == 7
        return self.current_key

    def add_user_key(self, key) -> None:
        self.keys.append(key)

    def add_private_key_bundle(self, bundle) -> None:
        self.bundles.append(bundle)

    def flush(self) -> None:
        if self.keys and self.keys[-1].id is None:
            self.keys[-1].id = 11


class FakeAudit:
    def __init__(self) -> None:
        self.events = []

    def append(self, **event) -> None:
        self.events.append(event)


def _service(repository: FakeRepository) -> tuple[KeyService, FakeDb, FakeAudit]:
    db = FakeDb()
    audit = FakeAudit()
    service = KeyService(
        db=db,
        settings=SimpleNamespace(USER_RSA_KEY_SIZE=2048),
        repository=repository,
        audit_service=audit,
        clock=lambda: NOW,
    )
    return service, db, audit


def test_current_private_key_authorizes_atomic_successor_addition() -> None:
    current_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    repository = FakeRepository(_pem(current_private_key))
    service, db, audit = _service(repository)
    addition = _addition(_pem(new_private_key))
    payload = service.get_addition_signing_payload(actor=_actor(), addition=addition)
    signature = current_private_key.sign(
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )

    key, bundle, profile = service.add_client_key(
        actor=_actor(),
        addition=addition,
        authorization_signature=signature,
        context=RequestContext(ip_address="203.0.113.4"),
    )

    assert len(payload) == 32
    assert db.commits == 1
    assert db.rollbacks == 0
    assert key.key_uuid == str(NEW_KEY_ID)
    assert key.status == "ACTIVE"
    assert bundle.bundle_uuid == str(BUNDLE_ID)
    assert bundle.user_key_id == key.id
    assert profile is repository.profile
    assert repository.current_key.key_uuid == str(CURRENT_KEY_ID)
    assert audit.events[0]["action"] == "USER_KEY_ADDED"


def test_signature_from_unrelated_key_cannot_add_account_key() -> None:
    current_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    unrelated_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    repository = FakeRepository(_pem(current_private_key))
    service, db, audit = _service(repository)
    addition = _addition(_pem(new_private_key))
    payload = service.get_addition_signing_payload(actor=_actor(), addition=addition)
    signature = unrelated_private_key.sign(
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )

    with pytest.raises(KeyBundleInvalidError):
        service.add_client_key(
            actor=_actor(),
            addition=addition,
            authorization_signature=signature,
            context=RequestContext(),
        )

    assert db.commits == 0
    assert db.rollbacks == 1
    assert not repository.keys
    assert not audit.events


def test_stale_authorizing_key_is_rejected_before_signing() -> None:
    current_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    repository = FakeRepository(_pem(current_private_key))
    repository.current_key.key_uuid = "77777777-7777-4777-8777-777777777777"
    service, _db, _audit = _service(repository)

    with pytest.raises(KeyBundleRevisionConflictError):
        service.get_addition_signing_payload(
            actor=_actor(),
            addition=_addition(_pem(new_private_key)),
        )


def test_current_private_key_authorizes_atomic_protection_rewrap() -> None:
    current_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    repository = FakeRepository(_pem(current_private_key))
    service, db, audit = _service(repository)
    protection = _protection()
    payload = service.get_rewrap_signing_payload(
        actor=_actor(),
        authorizing_key_id=CURRENT_KEY_ID,
        expected_revision=3,
        protection=protection,
    )
    signature = current_private_key.sign(
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )

    profile = service.rewrap_protection_profile(
        actor=_actor(),
        authorizing_key_id=CURRENT_KEY_ID,
        expected_revision=3,
        protection=protection,
        authorization_signature=signature,
        context=RequestContext(ip_address="203.0.113.5"),
    )

    assert len(payload) == 32
    assert db.commits == 1
    assert db.rollbacks == 0
    assert profile.revision == 4
    assert profile.kdf_salt == protection.kdf_salt
    assert profile.wrapped_amk == protection.wrapped_amk
    assert audit.events[0]["action"] == "KEY_PROTECTION_REWRAPPED"
    assert audit.events[0]["metadata"] == {
        "authorizing_key_id": str(CURRENT_KEY_ID),
        "previous_revision": 3,
        "revision": 4,
    }


def test_server_managed_profile_cannot_be_downgraded_by_legacy_rewrap() -> None:
    current_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    repository = FakeRepository(_pem(current_private_key))
    repository.profile.format_version = 2
    service, db, audit = _service(repository)

    with pytest.raises(KeyBundleRevisionConflictError, match="change-password"):
        service.get_rewrap_signing_payload(
            actor=_actor(),
            authorizing_key_id=CURRENT_KEY_ID,
            expected_revision=3,
            protection=_protection(),
        )
    with pytest.raises(KeyBundleRevisionConflictError, match="change-password"):
        service.rewrap_protection_profile(
            actor=_actor(),
            authorizing_key_id=CURRENT_KEY_ID,
            expected_revision=3,
            protection=_protection(),
            authorization_signature=b"x" * 256,
            context=RequestContext(),
        )

    assert repository.profile.revision == 3
    assert db.commits == 0
    assert db.rollbacks == 1
    assert not audit.events


def test_unrelated_private_key_cannot_rewrap_protection_profile() -> None:
    current_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    unrelated_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    repository = FakeRepository(_pem(current_private_key))
    service, db, audit = _service(repository)
    protection = _protection()
    payload = service.get_rewrap_signing_payload(
        actor=_actor(),
        authorizing_key_id=CURRENT_KEY_ID,
        expected_revision=3,
        protection=protection,
    )
    signature = unrelated_private_key.sign(
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )

    with pytest.raises(KeyBundleInvalidError):
        service.rewrap_protection_profile(
            actor=_actor(),
            authorizing_key_id=CURRENT_KEY_ID,
            expected_revision=3,
            protection=protection,
            authorization_signature=signature,
            context=RequestContext(),
        )

    assert repository.profile.revision == 3
    assert db.commits == 0
    assert db.rollbacks == 1
    assert not audit.events


def test_rewrap_digest_binds_actor_key_revision_and_every_protection_field() -> None:
    current_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    service, _db, _audit = _service(FakeRepository(_pem(current_private_key)))
    protection = _protection()

    def digest(
        candidate: KeyProtectionProfileInput = protection,
        *,
        actor: ActorContext = _actor(),
        key_id: UUID = CURRENT_KEY_ID,
        revision: int = 3,
    ) -> bytes:
        return service._rewrap_authorization_payload(
            actor=actor,
            authorizing_key_id=key_id,
            expected_revision=revision,
            protection=candidate,
        )

    baseline = digest()
    candidates = [
        digest(actor=replace(_actor(), user_public_id=NEW_KEY_ID)),
        digest(key_id=NEW_KEY_ID),
        digest(revision=4),
        digest(replace(protection, profile_id=NEW_KEY_ID)),
        digest(replace(protection, format_version=2)),
        digest(replace(protection, kdf_algorithm="ARGON2ID-V2")),
        digest(replace(protection, kdf_version=20)),
        digest(replace(protection, kdf_salt=b"x" * 16)),
        digest(replace(protection, kdf_memory_kib=131_072)),
        digest(replace(protection, kdf_iterations=4)),
        digest(replace(protection, kdf_parallelism=2)),
        digest(replace(protection, derived_key_length=64)),
        digest(replace(protection, amk_wrapping_algorithm="AES-256-GCM-V2")),
        digest(replace(protection, wrapped_amk=b"x" * 32)),
        digest(replace(protection, amk_nonce=b"x" * 12)),
        digest(replace(protection, amk_auth_tag=b"x" * 16)),
        digest(replace(protection, aad_version=2)),
    ]

    assert len(baseline) == 32
    assert all(candidate != baseline for candidate in candidates)
    assert len(set(candidates)) == len(candidates)
