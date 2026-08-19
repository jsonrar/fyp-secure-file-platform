from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.security import (
    PasswordOperationCapacityError,
    hash_auth_throttle_key,
    hash_session_token,
    normalize_password,
)
from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import LoginThrottleScope, SessionStatus, SystemRole, UserStatus
from app.domain.errors import (
    AuthenticationError,
    AuthenticationRateLimitedError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidRefreshTokenError,
)
from app.domain.keys import (
    EncryptedPrivateKeyBundleInput,
    GeneratedAccountKey,
    KeyProtectionProfileInput,
)
from app.models.encrypted_private_key_bundle import EncryptedPrivateKeyBundle
from app.models.session_refresh_token import SessionRefreshToken
from app.models.user import User
from app.models.user_key import UserKey
from app.models.user_key_protection_profile import UserKeyProtectionProfile
from app.models.user_session import UserSession
from app.services.auth_service import AuthService

NOW = datetime(2026, 8, 4, 4, 0, tzinfo=UTC)
NOW_DB = NOW.replace(tzinfo=None)
USER_PUBLIC_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_PUBLIC_ID = UUID("22222222-2222-4222-8222-222222222222")
NEXT_PUBLIC_ID = UUID("33333333-3333-4333-8333-333333333333")
KEY_ID = UUID("44444444-4444-4444-8444-444444444444")
PROFILE_ID = UUID("55555555-5555-4555-8555-555555555555")
BUNDLE_ID = UUID("66666666-6666-4666-8666-666666666666")
CONTEXT = RequestContext(ip_address="203.0.113.10", user_agent="auth-service-test")


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeAuditService:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.error: Exception | None = None

    def append(self, **event: Any) -> None:
        if self.error is not None:
            raise self.error
        self.events.append(event)


class FakeCryptoService:
    def __init__(self) -> None:
        self.generated_calls: list[dict[str, Any]] = []
        self.rewrap_calls: list[dict[str, Any]] = []

    def generate_account_key(self, **values: Any) -> GeneratedAccountKey:
        self.generated_calls.append(values)
        assert values["password"] == "A unique and lengthy passphrase!"
        assert values["key_id"] == KEY_ID
        assert values["profile_id"] == PROFILE_ID
        assert values["bundle_id"] == BUNDLE_ID
        assert values["key_size"] == 2048
        return _generated_key()

    def public_key_fingerprint(self, public_key_pem: str) -> str:
        assert public_key_pem == "PUBLIC KEY"
        return "f" * 64

    def rewrap_key_protection_profile(self, **values: Any) -> KeyProtectionProfileInput:
        self.rewrap_calls.append(values)
        return replace(
            values["protection"],
            kdf_salt=b"r" * 16,
            wrapped_amk=b"x" * 32,
            amk_nonce=b"m" * 12,
            amk_auth_tag=b"g" * 16,
        )


class FakePasswordManager:
    def __init__(self) -> None:
        self.verify_or_dummy_calls: list[tuple[str, str | None]] = []
        self.verify_or_dummy_commit_counts: list[int] = []
        self.verify_and_update_calls: list[tuple[str, str]] = []
        self.capacity_exhausted = False
        self.db: FakeDb | None = None

    def hash(self, password: str) -> str:
        if self.capacity_exhausted:
            raise PasswordOperationCapacityError()
        return f"hash::{normalize_password(password)}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        if self.capacity_exhausted:
            raise PasswordOperationCapacityError()
        return self.hash(plain_password) == password_hash

    def verify_and_update(
        self,
        plain_password: str,
        password_hash: str,
    ) -> tuple[bool, str | None]:
        self.verify_and_update_calls.append((plain_password, password_hash))
        return self.verify(plain_password, password_hash), None

    def verify_or_dummy(
        self,
        plain_password: str,
        password_hash: str | None,
    ) -> tuple[bool, str | None]:
        if self.capacity_exhausted:
            raise PasswordOperationCapacityError()
        self.verify_or_dummy_calls.append((plain_password, password_hash))
        if self.db is not None:
            self.verify_or_dummy_commit_counts.append(self.db.commits)
        if password_hash is None:
            return False, None
        return self.verify(plain_password, password_hash), None


class SequenceFactory:
    def __init__(self, values: list[Any]) -> None:
        self._values = iter(values)

    def __call__(self) -> Any:
        return next(self._values)


class FakeAuthRepository:
    def __init__(self) -> None:
        self.identifier_taken = False
        self.user_by_username: User | None = None
        self.locked_user: User | None = None
        self.user: User | None = None
        self.principal: tuple[UserSession, User] | None = None
        self.locked_session: UserSession | None = None
        self.locked_refresh_token: SessionRefreshToken | None = None
        self.blocked_until: datetime | None = None
        self.active_sessions: list[UserSession] = []
        self.sessions: list[UserSession] = []
        self.revoke_all_count = 0

        self.added_users: list[User] = []
        self.added_user_keys: list[UserKey] = []
        self.added_key_protection_profiles: list[UserKeyProtectionProfile] = []
        self.added_private_key_bundles: list[EncryptedPrivateKeyBundle] = []
        self.added_sessions: list[UserSession] = []
        self.added_refresh_tokens: list[SessionRefreshToken] = []
        self.key_protection_profile: UserKeyProtectionProfile | None = None
        self.revocations: list[tuple[UserSession, datetime, str]] = []
        self.expirations: list[tuple[UserSession, datetime]] = []
        self.clear_throttle_calls: list[tuple[LoginThrottleScope, str]] = []
        self.throttles: dict[tuple[LoginThrottleScope, str], SimpleNamespace] = {}

    def username_exists(self, username: str) -> bool:
        return self.identifier_taken

    def add_user(self, user: User) -> None:
        self.added_users.append(user)

    def add_user_key(self, user_key: UserKey) -> None:
        self.added_user_keys.append(user_key)

    def add_key_protection_profile(self, profile: UserKeyProtectionProfile) -> None:
        self.added_key_protection_profiles.append(profile)

    def add_private_key_bundle(self, bundle: EncryptedPrivateKeyBundle) -> None:
        self.added_private_key_bundles.append(bundle)

    def add_session(self, user_session: UserSession) -> None:
        self.added_sessions.append(user_session)

    def add_refresh_token(self, refresh_token: SessionRefreshToken) -> None:
        self.added_refresh_tokens.append(refresh_token)

    def flush(self) -> None:
        for index, user in enumerate(self.added_users, start=1):
            if user.id is None:
                user.id = index
        for index, user_session in enumerate(self.added_sessions, start=10):
            if user_session.id is None:
                user_session.id = index
        for index, user_key in enumerate(self.added_user_keys, start=20):
            if user_key.id is None:
                user_key.id = index

    def get_blocked_until(
        self,
        buckets: tuple[tuple[LoginThrottleScope, str], ...],
        *,
        now: datetime,
    ) -> datetime | None:
        return self.blocked_until

    def get_user_by_username(self, username: str) -> User | None:
        return self.user_by_username

    def lock_user(self, user_id: int) -> User | None:
        return self.locked_user

    def lock_key_protection_profile(self, user_id: int) -> UserKeyProtectionProfile | None:
        return self.key_protection_profile

    def get_user(self, user_id: int) -> User | None:
        return self.user

    def clear_throttle(self, scope: LoginThrottleScope, key_hash: str) -> None:
        self.clear_throttle_calls.append((scope, key_hash))
        self.throttles.pop((scope, key_hash), None)

    def lock_active_sessions(self, user_id: int) -> list[UserSession]:
        return list(self.active_sessions)

    def lock_or_create_throttle(
        self,
        scope: LoginThrottleScope,
        key_hash: str,
        *,
        now: datetime,
    ) -> SimpleNamespace:
        key = (scope, key_hash)
        if key not in self.throttles:
            self.throttles[key] = SimpleNamespace(
                failed_count=0,
                window_started_at=now,
                blocked_until=None,
                updated_at=now,
            )
        return self.throttles[key]

    def get_access_principal(self, access_token_hash: str) -> tuple[UserSession, User] | None:
        return self.principal

    def lock_session(self, session_id: int) -> UserSession | None:
        return self.locked_session

    def lock_refresh_token(self, token_hash: str) -> SessionRefreshToken | None:
        return self.locked_refresh_token

    def get_refresh_route(self, token_hash: str) -> tuple[int, int] | None:
        if self.locked_refresh_token is None or self.locked_session is None:
            return None
        return self.locked_refresh_token.session_id, self.locked_session.user_id

    def revoke_session_family(
        self,
        user_session: UserSession,
        *,
        now: datetime,
        reason: str,
    ) -> bool:
        changed = user_session.status == SessionStatus.ACTIVE
        if changed:
            user_session.status = SessionStatus.REVOKED
            user_session.revoked_at = now
            user_session.revoked_reason = reason
        self.revocations.append((user_session, now, reason))
        return changed

    def expire_session_family(self, user_session: UserSession, *, now: datetime) -> bool:
        changed = user_session.status == SessionStatus.ACTIVE
        if changed:
            user_session.status = SessionStatus.EXPIRED
            user_session.revoked_at = now
            user_session.revoked_reason = "absolute_expiry"
        self.expirations.append((user_session, now))
        return changed

    def revoke_all_session_families(
        self,
        user_id: int,
        *,
        now: datetime,
        reason: str,
    ) -> int:
        self.revocations.extend((item, now, reason) for item in self.active_sessions)
        return self.revoke_all_count

    def list_sessions(self, user_id: int) -> list[UserSession]:
        return list(self.sessions)

    def lock_session_for_user(
        self,
        user_id: int,
        session_id: UUID,
    ) -> UserSession | None:
        return self.locked_session


@dataclass
class Harness:
    service: AuthService
    db: FakeDb
    repository: FakeAuthRepository
    audit: FakeAuditService
    passwords: FakePasswordManager
    crypto: FakeCryptoService


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        APP_DEBUG=False,
        SECRET_KEY="test-secret-key-that-is-long-enough",
        USER_RSA_KEY_SIZE=2048,
    )


def _harness() -> Harness:
    db = FakeDb()
    repository = FakeAuthRepository()
    audit = FakeAuditService()
    passwords = FakePasswordManager()
    passwords.db = db
    crypto = FakeCryptoService()
    service = AuthService(
        db=db,  # type: ignore[arg-type]
        settings=_settings(),
        repository=repository,  # type: ignore[arg-type]
        audit_service=audit,  # type: ignore[arg-type]
        crypto_service=crypto,  # type: ignore[arg-type]
        passwords=passwords,  # type: ignore[arg-type]
        clock=lambda: NOW,
        token_factory=SequenceFactory(
            [
                "access-token-material-a" * 2,
                "refresh-token-material-a" * 2,
                "access-token-material-b" * 2,
                "refresh-token-material-b" * 2,
            ]
        ),
        uuid_factory=SequenceFactory(
            [USER_PUBLIC_ID, KEY_ID, PROFILE_ID, BUNDLE_ID, SESSION_PUBLIC_ID, NEXT_PUBLIC_ID]
        ),
    )
    return Harness(service, db, repository, audit, passwords, crypto)


def _user(
    *,
    status: UserStatus = UserStatus.ACTIVE,
    password: str = "Current secure passphrase!",
) -> User:
    return User(
        id=7,
        user_uuid=str(USER_PUBLIC_ID),
        username="alice",
        email="alice@example.com",
        password_hash=f"hash::{password}",
        role=SystemRole.USER,
        status=status,
        email_verified=False,
        created_at=NOW_DB - timedelta(days=30),
        updated_at=NOW_DB - timedelta(days=1),
        password_changed_at=NOW_DB - timedelta(days=30),
    )


def _session(
    *,
    status: SessionStatus = SessionStatus.ACTIVE,
    access_token: str = "at_existing-access-token-material-000000",
    access_expires_at: datetime | None = None,
    absolute_expires_at: datetime | None = None,
) -> UserSession:
    return UserSession(
        id=9,
        session_uuid=str(SESSION_PUBLIC_ID),
        user_id=7,
        access_token_hash=hash_session_token(access_token),
        status=status,
        created_at=NOW_DB - timedelta(hours=1),
        updated_at=NOW_DB - timedelta(hours=1),
        access_expires_at=access_expires_at or NOW_DB + timedelta(minutes=30),
        absolute_expires_at=absolute_expires_at or NOW_DB + timedelta(days=1),
    )


def _actor(session: UserSession | None = None) -> ActorContext:
    active_session = session or _session()
    return ActorContext(
        user_id=7,
        user_public_id=USER_PUBLIC_ID,
        session_id=active_session.id,
        session_public_id=SESSION_PUBLIC_ID,
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
        access_token_hash=active_session.access_token_hash,
    )


def _generated_key() -> GeneratedAccountKey:
    encrypted_private_key = b"client-encrypted-pkcs8" * 20
    return GeneratedAccountKey(
        key_id=KEY_ID,
        public_key_pem="PUBLIC KEY",
        algorithm="RSA-OAEP-SHA256",
        key_size_bits=2048,
        protection=KeyProtectionProfileInput(
            profile_id=PROFILE_ID,
            format_version=2,
            kdf_algorithm="ARGON2ID",
            kdf_version=19,
            kdf_salt=b"s" * 16,
            kdf_memory_kib=65_536,
            kdf_iterations=3,
            kdf_parallelism=4,
            derived_key_length=32,
            amk_wrapping_algorithm="AES-256-GCM",
            wrapped_amk=b"w" * 32,
            amk_nonce=b"n" * 12,
            amk_auth_tag=b"t" * 16,
            aad_version=1,
        ),
        private_key_bundle=EncryptedPrivateKeyBundleInput(
            bundle_id=BUNDLE_ID,
            format_version=2,
            private_key_format="PKCS8-DER",
            derivation_algorithm="HKDF-SHA256",
            derivation_salt=b"d" * 16,
            encryption_algorithm="AES-256-GCM",
            encrypted_private_key=encrypted_private_key,
            nonce=b"i" * 12,
            auth_tag=b"a" * 16,
            aad_version=1,
            ciphertext_sha256=__import__("hashlib").sha256(encrypted_private_key).hexdigest(),
        ),
    )


def _server_managed_protection_profile() -> UserKeyProtectionProfile:
    return UserKeyProtectionProfile(
        user_id=7,
        profile_uuid=str(PROFILE_ID),
        format_version=2,
        kdf_algorithm="ARGON2ID",
        kdf_version=19,
        kdf_salt=b"s" * 16,
        kdf_memory_kib=65_536,
        kdf_iterations=3,
        kdf_parallelism=4,
        derived_key_length=32,
        amk_wrapping_algorithm="AES-256-GCM",
        wrapped_amk=b"w" * 32,
        amk_nonce=b"n" * 12,
        amk_auth_tag=b"t" * 16,
        aad_version=1,
        revision=1,
        created_at=NOW_DB - timedelta(days=30),
        updated_at=NOW_DB - timedelta(days=30),
    )


def test_register_generates_and_persists_encrypted_key_material() -> None:
    harness = _harness()

    result = harness.service.register(
        username=" alice ",
        password="A unique and lengthy passphrase!",
        context=CONTEXT,
    )

    user = harness.repository.added_users[0]
    user_key = harness.repository.added_user_keys[0]
    assert result.user.id == USER_PUBLIC_ID
    assert result.key_id == KEY_ID
    assert result.public_key_fingerprint == "f" * 64
    assert user.username == "alice"
    assert user.email == f"{USER_PUBLIC_ID}@demo.invalid"
    assert user.password_hash == "hash::A unique and lengthy passphrase!"
    assert user_key.user_id == user.id
    assert user_key.key_uuid == str(KEY_ID)
    assert user_key.public_key_pem == "PUBLIC KEY"
    assert user_key.fingerprint == "f" * 64
    assert user_key.custody_mode == "CLIENT_WRAPPED"
    assert harness.repository.added_key_protection_profiles[0].wrapped_amk == b"w" * 32
    assert (
        harness.repository.added_private_key_bundles[0].encrypted_private_key
        == b"client-encrypted-pkcs8" * 20
    )
    assert "A unique and lengthy passphrase!" not in repr(
        [
            vars(user_key),
            vars(harness.repository.added_key_protection_profiles[0]),
            vars(harness.repository.added_private_key_bundles[0]),
        ]
    )
    assert harness.audit.events[-1]["action"] == "AUTH_REGISTERED"
    assert len(harness.crypto.generated_calls) == 1
    assert {scope for scope, _ in harness.repository.throttles} == {
        LoginThrottleScope.REGISTRATION_IP
    }
    # Registration throttling is committed independently before the account transaction.
    assert harness.db.commits == 2
    assert harness.db.rollbacks == 0


def test_register_rolls_back_when_atomic_audit_write_fails() -> None:
    harness = _harness()
    harness.audit.error = RuntimeError("audit unavailable")

    with pytest.raises(RuntimeError, match="audit unavailable"):
        harness.service.register(
            username="alice",
            password="A unique and lengthy passphrase!",
            context=CONTEXT,
        )

    # The registration throttle survives; the account/key/audit transaction does not.
    assert harness.db.commits == 1
    assert harness.db.rollbacks == 1


def test_unknown_login_runs_dummy_verification_and_commits_failure_audit() -> None:
    harness = _harness()

    with pytest.raises(InvalidCredentialsError):
        harness.service.login(
            username="unknown-user",
            password="incorrect-password",
            context=CONTEXT,
        )

    assert harness.passwords.verify_or_dummy_calls == [("incorrect-password", None)]
    assert harness.passwords.verify_or_dummy_commit_counts == [1]
    assert len(harness.repository.throttles) == 2
    assert harness.audit.events[-1]["action"] == "AUTH_LOGIN_FAILED"
    assert harness.db.commits == 2
    assert harness.db.rollbacks == 1
    assert not harness.repository.added_sessions


def test_successful_login_stores_only_token_hashes_and_returns_raw_tokens() -> None:
    harness = _harness()
    user = _user()
    harness.repository.user_by_username = user
    harness.repository.locked_user = user

    result = harness.service.login(
        username=" alice ",
        password="Current secure passphrase!",
        context=CONTEXT,
    )

    user_session = harness.repository.added_sessions[0]
    refresh_token = harness.repository.added_refresh_tokens[0]
    assert result.tokens.access_token.startswith("at_")
    assert result.tokens.refresh_token.startswith("rt_")
    assert user_session.access_token_hash == hash_session_token(result.tokens.access_token)
    assert refresh_token.token_hash == hash_session_token(result.tokens.refresh_token)
    assert result.tokens.access_token != user_session.access_token_hash
    assert result.tokens.refresh_token != refresh_token.token_hash
    assert refresh_token.generation == 0
    assert user.last_login_at == NOW_DB
    assert harness.audit.events[-1]["action"] == "AUTH_LOGIN_SUCCEEDED"
    assert harness.db.commits == 2


def test_login_password_capacity_failure_does_not_record_a_password_failure() -> None:
    harness = _harness()
    harness.passwords.capacity_exhausted = True

    with pytest.raises(AuthenticationRateLimitedError) as exc_info:
        harness.service.login(
            username="alice",
            password="Current secure passphrase!",
            context=CONTEXT,
        )

    assert exc_info.value.headers["Retry-After"] == "1"
    assert {item.failed_count for item in harness.repository.throttles.values()} == {0}
    assert harness.audit.events == []
    assert harness.db.commits == 1
    assert harness.db.rollbacks == 1


def test_refresh_rotates_both_tokens_and_consumes_previous_generation() -> None:
    harness = _harness()
    raw_refresh_token = "rt_existing-refresh-token-material-000000"
    user = _user()
    user_session = _session()
    stored_token = SessionRefreshToken(
        id=20,
        session_id=user_session.id,
        token_hash=hash_session_token(raw_refresh_token),
        generation=4,
        created_at=NOW_DB
        - timedelta(seconds=harness.service.settings.AUTH_REFRESH_MIN_INTERVAL_SECONDS),
        expires_at=NOW_DB + timedelta(days=1),
    )
    harness.repository.locked_refresh_token = stored_token
    harness.repository.locked_session = user_session
    harness.repository.locked_user = user

    result = harness.service.refresh(refresh_token=raw_refresh_token, context=CONTEXT)

    rotated_token = harness.repository.added_refresh_tokens[-1]
    assert stored_token.consumed_at == NOW_DB
    assert rotated_token.generation == 5
    assert rotated_token.token_hash == hash_session_token(result.tokens.refresh_token)
    assert user_session.access_token_hash == hash_session_token(result.tokens.access_token)
    assert harness.audit.events[-1]["action"] == "AUTH_SESSION_REFRESHED"
    assert harness.db.commits == 1


def test_refresh_rate_limit_does_not_consume_or_audit_token() -> None:
    harness = _harness()
    raw_refresh_token = "rt_new-refresh-token-material-000000000"
    user = _user()
    user_session = _session()
    stored_token = SessionRefreshToken(
        id=20,
        session_id=user_session.id,
        token_hash=hash_session_token(raw_refresh_token),
        generation=0,
        created_at=NOW_DB,
        expires_at=NOW_DB + timedelta(days=1),
    )
    harness.repository.locked_refresh_token = stored_token
    harness.repository.locked_session = user_session
    harness.repository.locked_user = user

    with pytest.raises(AuthenticationRateLimitedError) as exc_info:
        harness.service.refresh(refresh_token=raw_refresh_token, context=CONTEXT)

    assert exc_info.value.headers["Retry-After"] == str(
        harness.service.settings.AUTH_REFRESH_MIN_INTERVAL_SECONDS
    )
    assert stored_token.consumed_at is None
    assert harness.repository.added_refresh_tokens == []
    assert harness.audit.events == []
    assert harness.db.rollbacks == 1


def test_refresh_replay_revokes_entire_session_family_before_rejecting() -> None:
    harness = _harness()
    raw_refresh_token = "rt_replayed-refresh-token-material-00000"
    user = _user()
    user_session = _session()
    stored_token = SessionRefreshToken(
        id=20,
        session_id=user_session.id,
        token_hash=hash_session_token(raw_refresh_token),
        generation=1,
        created_at=NOW_DB,
        expires_at=NOW_DB + timedelta(days=1),
        consumed_at=NOW_DB,
    )
    harness.repository.locked_refresh_token = stored_token
    harness.repository.locked_session = user_session
    harness.repository.locked_user = user

    with pytest.raises(InvalidRefreshTokenError):
        harness.service.refresh(refresh_token=raw_refresh_token, context=CONTEXT)

    assert user_session.status == SessionStatus.REVOKED
    assert user_session.revoked_reason == "refresh_token_reuse"
    assert harness.repository.revocations[-1][2] == "refresh_token_reuse"
    assert harness.audit.events[-1]["action"] == "AUTH_REFRESH_REPLAY_DETECTED"
    assert harness.db.commits == 1
    assert harness.db.rollbacks == 1


@pytest.mark.parametrize(
    ("status", "access_expires_at"),
    [
        (SessionStatus.REVOKED, NOW_DB + timedelta(minutes=1)),
        (SessionStatus.ACTIVE, NOW_DB),
    ],
)
def test_authenticate_rejects_revoked_or_expired_access_session(
    status: SessionStatus,
    access_expires_at: datetime,
) -> None:
    harness = _harness()
    raw_token = "at_existing-access-token-material-000000"
    harness.repository.principal = (
        _session(status=status, access_token=raw_token, access_expires_at=access_expires_at),
        _user(),
    )

    with pytest.raises(AuthenticationError):
        harness.service.authenticate_access_token(raw_token)


def test_logout_revokes_only_actor_current_session() -> None:
    harness = _harness()
    user_session = _session()
    harness.repository.locked_session = user_session

    harness.service.logout(actor=_actor(user_session), context=CONTEXT)

    assert user_session.status == SessionStatus.REVOKED
    assert user_session.revoked_reason == "logout"
    assert harness.repository.revocations[-1][0] is user_session
    assert harness.audit.events[-1]["action"] == "AUTH_LOGGED_OUT"
    assert harness.db.commits == 1


def test_logout_all_revokes_every_active_session_for_actor() -> None:
    harness = _harness()
    harness.repository.active_sessions = [_session(), _session()]
    harness.repository.revoke_all_count = 2

    revoked = harness.service.logout_all(actor=_actor(), context=CONTEXT)

    assert revoked == 2
    assert all(item[2] == "logout_all" for item in harness.repository.revocations)
    assert harness.audit.events[-1]["metadata"] == {"revoked_sessions": 2}
    assert harness.db.commits == 1


def test_change_password_rehashes_and_revokes_all_sessions() -> None:
    harness = _harness()
    user = _user()
    harness.repository.user = user
    harness.repository.locked_user = user
    harness.repository.revoke_all_count = 3

    revoked = harness.service.change_password(
        actor=_actor(),
        current_password="Current secure passphrase!",
        new_password="A completely new secure phrase!",
        context=CONTEXT,
    )

    assert revoked == 3
    assert user.password_hash == "hash::A completely new secure phrase!"
    assert user.password_changed_at == NOW_DB
    assert harness.audit.events[-1]["action"] == "AUTH_PASSWORD_CHANGED"
    assert harness.audit.events[-1]["metadata"] == {"revoked_sessions": 3}
    assert harness.repository.clear_throttle_calls[-1][0] == LoginThrottleScope.REAUTH_ACCOUNT
    assert harness.db.commits == 2


def test_change_password_rewraps_server_managed_key_protection() -> None:
    harness = _harness()
    user = _user()
    protection = _server_managed_protection_profile()
    harness.repository.user = user
    harness.repository.locked_user = user
    harness.repository.key_protection_profile = protection

    harness.service.change_password(
        actor=_actor(),
        current_password="Current secure passphrase!",
        new_password="A completely new secure phrase!",
        context=CONTEXT,
    )

    assert len(harness.crypto.rewrap_calls) == 1
    assert harness.crypto.rewrap_calls[0]["current_password"] == ("Current secure passphrase!")
    assert harness.crypto.rewrap_calls[0]["new_password"] == ("A completely new secure phrase!")
    assert protection.kdf_salt == b"r" * 16
    assert protection.wrapped_amk == b"x" * 32
    assert protection.amk_nonce == b"m" * 12
    assert protection.amk_auth_tag == b"g" * 16
    assert protection.revision == 2
    assert protection.updated_at == NOW_DB
    assert harness.audit.events[-1]["metadata"] == {
        "revoked_sessions": 0,
        "key_protection_rewrapped": True,
    }


def test_invalid_current_password_is_throttled_and_audited() -> None:
    harness = _harness()
    harness.repository.user = _user()

    with pytest.raises(InvalidCurrentPasswordError):
        harness.service.change_password(
            actor=_actor(),
            current_password="An incorrect current passphrase!",
            new_password="A completely new secure phrase!",
            context=CONTEXT,
        )

    assert len(harness.repository.throttles) == 2
    assert {scope for scope, _ in harness.repository.throttles} == {
        LoginThrottleScope.REAUTH_ACCOUNT,
        LoginThrottleScope.REAUTH_IP,
    }
    assert harness.audit.events[-1]["action"] == "AUTH_PASSWORD_CHANGE_FAILED"
    assert harness.db.commits == 2
    assert harness.db.rollbacks == 1


def test_reauthentication_block_does_not_block_public_login() -> None:
    harness = _harness()
    for bucket in harness.service._reauthentication_buckets("alice", CONTEXT):
        harness.repository.throttles[bucket] = SimpleNamespace(
            failed_count=100,
            window_started_at=NOW_DB,
            blocked_until=NOW_DB + timedelta(minutes=5),
            updated_at=NOW_DB,
        )
    user = _user()
    harness.repository.user_by_username = user
    harness.repository.locked_user = user

    result = harness.service.login(
        username="alice",
        password="Current secure passphrase!",
        context=CONTEXT,
    )

    assert result.user.id == USER_PUBLIC_ID
    assert harness.audit.events[-1]["action"] == "AUTH_LOGIN_SUCCEEDED"


def test_public_login_block_does_not_block_password_reauthentication() -> None:
    harness = _harness()
    for bucket in harness.service._login_buckets("alice", CONTEXT):
        harness.repository.throttles[bucket] = SimpleNamespace(
            failed_count=100,
            window_started_at=NOW_DB,
            blocked_until=NOW_DB + timedelta(minutes=5),
            updated_at=NOW_DB,
        )
    user = _user()
    harness.repository.user = user
    harness.repository.locked_user = user

    harness.service.change_password(
        actor=_actor(),
        current_password="Current secure passphrase!",
        new_password="A completely new secure phrase!",
        context=CONTEXT,
    )

    assert harness.audit.events[-1]["action"] == "AUTH_PASSWORD_CHANGED"


def test_login_account_and_ip_throttles_use_independent_limits() -> None:
    harness = _harness()
    harness.repository.user_by_username = None

    for _ in range(harness.service.settings.AUTH_LOGIN_ACCOUNT_MAX_FAILURES):
        with pytest.raises(InvalidCredentialsError):
            harness.service.login(
                username="alice",
                password="An incorrect current passphrase!",
                context=CONTEXT,
            )

    throttles = harness.repository.throttles
    account = next(
        item for (scope, _), item in throttles.items() if scope == LoginThrottleScope.ACCOUNT
    )
    ip = next(item for (scope, _), item in throttles.items() if scope == LoginThrottleScope.IP)
    assert account.blocked_until == NOW_DB + timedelta(
        seconds=harness.service.settings.AUTH_LOGIN_ACCOUNT_BLOCK_SECONDS
    )
    assert ip.blocked_until is None

    completed_verifications = len(harness.passwords.verify_or_dummy_calls)
    with pytest.raises(AuthenticationRateLimitedError):
        harness.service.login(
            username="alice",
            password="An incorrect current passphrase!",
            context=CONTEXT,
        )
    assert len(harness.passwords.verify_or_dummy_calls) == completed_verifications


def test_blocked_login_attempt_does_not_extend_existing_lockout() -> None:
    harness = _harness()
    account_bucket = harness.service._login_buckets(
        "alice",
        RequestContext(),
    )[0]
    original_blocked_until = NOW_DB + timedelta(
        seconds=harness.service.settings.AUTH_LOGIN_ACCOUNT_BLOCK_SECONDS
    )
    throttle = SimpleNamespace(
        failed_count=harness.service.settings.AUTH_LOGIN_ACCOUNT_MAX_FAILURES,
        window_started_at=NOW_DB,
        blocked_until=original_blocked_until,
        updated_at=NOW_DB,
    )
    harness.repository.throttles[account_bucket] = throttle

    with pytest.raises(AuthenticationRateLimitedError) as exc_info:
        harness.service._check_login_attempt_allowed(
            (account_bucket,),
            now=NOW_DB + timedelta(minutes=1),
        )

    assert throttle.blocked_until == original_blocked_until
    assert exc_info.value.headers["Retry-After"] == str(
        int((original_blocked_until - (NOW_DB + timedelta(minutes=1))).total_seconds())
    )

    # A verification already in flight when another request created the block
    # may still finish as a failure; it must not extend that existing deadline.
    harness.service._record_login_failure(
        (account_bucket,),
        now=NOW_DB + timedelta(minutes=1),
    )
    assert throttle.blocked_until == original_blocked_until


def test_registration_rechecks_block_after_lock_before_expensive_work() -> None:
    harness = _harness()
    registration_bucket = (
        LoginThrottleScope.REGISTRATION_IP,
        hash_auth_throttle_key(
            harness.service.settings.SECRET_KEY,
            LoginThrottleScope.REGISTRATION_IP.value,
            CONTEXT.ip_address or "",
        ),
    )
    harness.repository.throttles[registration_bucket] = SimpleNamespace(
        failed_count=harness.service.settings.AUTH_REGISTRATION_MAX_ATTEMPTS,
        window_started_at=NOW_DB,
        blocked_until=NOW_DB + timedelta(minutes=10),
        updated_at=NOW_DB,
    )

    with pytest.raises(AuthenticationRateLimitedError):
        harness.service.register(
            username="alice",
            password="A unique and lengthy passphrase!",
            context=CONTEXT,
        )

    assert harness.repository.added_users == []
    assert harness.audit.events == []
