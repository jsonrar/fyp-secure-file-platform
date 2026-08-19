import hashlib
from dataclasses import replace
from uuid import UUID

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.security import PasswordManager
from app.domain.keys import GeneratedAccountKey
from app.services.crypto_service import SERVER_MANAGED_KEY_FORMAT_VERSION, CryptoService

KEY_ID = UUID("11111111-1111-4111-8111-111111111111")
PROFILE_ID = UUID("22222222-2222-4222-8222-222222222222")
BUNDLE_ID = UUID("33333333-3333-4333-8333-333333333333")
PASSWORD = "A long login password for encryption!"


def _public_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )


@pytest.fixture(scope="module")
def password_manager() -> PasswordManager:
    return PasswordManager(max_concurrent_operations=1)


@pytest.fixture(scope="module")
def generated_registration(password_manager: PasswordManager) -> GeneratedAccountKey:
    return CryptoService().generate_account_key(
        password=PASSWORD,
        password_manager=password_manager,
        key_id=KEY_ID,
        profile_id=PROFILE_ID,
        bundle_id=BUNDLE_ID,
        key_size=2048,
        kdf_iterations=1,
        kdf_parallelism=1,
    )


def test_public_key_fingerprint_is_stable_sha256_identity() -> None:
    service = CryptoService()
    first_public_key = _public_key_pem()
    second_public_key = _public_key_pem()

    first_fingerprint = service.public_key_fingerprint(first_public_key)

    assert service.public_key_fingerprint(first_public_key) == first_fingerprint
    assert len(first_fingerprint) == 64
    assert first_fingerprint == first_fingerprint.lower()
    int(first_fingerprint, 16)
    assert service.public_key_fingerprint(second_public_key) != first_fingerprint


def test_generated_password_wrapped_key_decrypts_and_matches_public_key(
    password_manager: PasswordManager,
    generated_registration: GeneratedAccountKey,
) -> None:
    service = CryptoService()

    private_key = service.decrypt_account_private_key(
        password=PASSWORD,
        password_manager=password_manager,
        registration=generated_registration,
    )
    public_key = service.load_rsa_public_key(generated_registration.public_key_pem)

    assert generated_registration.protection.format_version == SERVER_MANAGED_KEY_FORMAT_VERSION
    assert (
        generated_registration.private_key_bundle.format_version
        == SERVER_MANAGED_KEY_FORMAT_VERSION
    )
    assert generated_registration.key_size_bits == 2048
    assert private_key.public_key().public_numbers() == public_key.public_numbers()
    assert len(generated_registration.protection.wrapped_amk) == 32
    assert len(generated_registration.private_key_bundle.auth_tag) == 16


def test_wrong_password_and_tampered_ciphertext_cannot_decrypt_generated_key(
    password_manager: PasswordManager,
    generated_registration: GeneratedAccountKey,
) -> None:
    service = CryptoService()

    with pytest.raises(ValueError, match="password or encrypted key material"):
        service.decrypt_account_private_key(
            password="The wrong login password!",
            password_manager=password_manager,
            registration=generated_registration,
        )

    bundle = generated_registration.private_key_bundle
    tampered_ciphertext = (
        bytes([bundle.encrypted_private_key[0] ^ 1]) + bundle.encrypted_private_key[1:]
    )
    tampered_bundle = replace(
        bundle,
        encrypted_private_key=tampered_ciphertext,
        ciphertext_sha256=hashlib.sha256(tampered_ciphertext).hexdigest(),
    )
    with pytest.raises(ValueError, match="password or encrypted key material"):
        service.decrypt_account_private_key(
            password=PASSWORD,
            password_manager=password_manager,
            registration=replace(
                generated_registration,
                private_key_bundle=tampered_bundle,
            ),
        )

    with pytest.raises(ValueError, match="password or encrypted key material"):
        service.decrypt_account_private_key(
            password=PASSWORD,
            password_manager=password_manager,
            registration=replace(
                generated_registration,
                key_id=UUID("44444444-4444-4444-8444-444444444444"),
            ),
        )


def test_password_rewrap_preserves_profile_identity_and_rotates_envelope(
    password_manager: PasswordManager,
    generated_registration: GeneratedAccountKey,
) -> None:
    service = CryptoService()
    protection = generated_registration.protection
    new_password = "A different long login password!"

    rewrapped = service.rewrap_key_protection_profile(
        current_password=PASSWORD,
        new_password=new_password,
        password_manager=password_manager,
        protection=protection,
    )

    assert rewrapped.profile_id == protection.profile_id
    assert rewrapped.format_version == protection.format_version
    assert rewrapped.aad_version == protection.aad_version
    assert rewrapped.kdf_algorithm == protection.kdf_algorithm
    assert rewrapped.kdf_version == protection.kdf_version
    assert rewrapped.kdf_memory_kib == protection.kdf_memory_kib
    assert rewrapped.kdf_iterations == protection.kdf_iterations
    assert rewrapped.kdf_parallelism == protection.kdf_parallelism
    assert rewrapped.derived_key_length == protection.derived_key_length
    assert rewrapped.amk_wrapping_algorithm == protection.amk_wrapping_algorithm
    assert rewrapped.kdf_salt != protection.kdf_salt
    assert rewrapped.amk_nonce != protection.amk_nonce
    assert rewrapped.wrapped_amk != protection.wrapped_amk
    assert rewrapped.amk_auth_tag != protection.amk_auth_tag

    updated_registration = replace(generated_registration, protection=rewrapped)
    service.decrypt_account_private_key(
        password=new_password,
        password_manager=password_manager,
        registration=updated_registration,
    )
    with pytest.raises(ValueError, match="password or encrypted key material"):
        service.decrypt_account_private_key(
            password=PASSWORD,
            password_manager=password_manager,
            registration=updated_registration,
        )


def test_rsa_pss_signature_authorizes_exact_payload_only() -> None:
    service = CryptoService()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )
    payload = b"canonical key mutation digest"
    signature = private_key.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=hashes.SHA256.digest_size,
        ),
        hashes.SHA256(),
    )

    service.verify_rsa_pss_sha256_signature(
        public_key_pem=public_key_pem,
        message=payload,
        signature=signature,
    )
    with pytest.raises(ValueError, match="invalid"):
        service.verify_rsa_pss_sha256_signature(
            public_key_pem=public_key_pem,
            message=payload + b"!",
            signature=signature,
        )
