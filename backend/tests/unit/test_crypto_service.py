import pytest
from cryptography.exceptions import InvalidTag

from app.services.crypto_service import CryptoService


def test_aes_gcm_round_trip() -> None:
    service = CryptoService()
    plaintext = b"confidential file contents"

    encrypted = service.encrypt_bytes(plaintext)
    decrypted = service.decrypt_bytes(
        encrypted.ciphertext,
        encrypted.file_key,
        encrypted.iv,
        encrypted.auth_tag,
    )

    assert decrypted == plaintext
    assert encrypted.ciphertext != plaintext


def test_aes_gcm_rejects_tampered_ciphertext() -> None:
    service = CryptoService()
    encrypted = service.encrypt_bytes(b"confidential file contents")
    tampered = bytes([encrypted.ciphertext[0] ^ 1]) + encrypted.ciphertext[1:]

    with pytest.raises(InvalidTag):
        service.decrypt_bytes(
            tampered,
            encrypted.file_key,
            encrypted.iv,
            encrypted.auth_tag,
        )


def test_rsa_key_wrapping_round_trip() -> None:
    service = CryptoService()
    private_key, public_key = service.generate_rsa_key_pair()
    file_key = service.generate_aes_key()

    wrapped = service.wrap_file_key(file_key, public_key)

    assert wrapped != file_key
    assert service.unwrap_file_key(wrapped, private_key) == file_key


def test_public_key_fingerprint_is_stable_sha256_identity() -> None:
    service = CryptoService()
    _, first_public_key = service.generate_rsa_key_pair(key_size=2048)
    _, second_public_key = service.generate_rsa_key_pair(key_size=2048)

    first_fingerprint = service.public_key_fingerprint(first_public_key)

    assert service.public_key_fingerprint(first_public_key) == first_fingerprint
    assert len(first_fingerprint) == 64
    assert first_fingerprint == first_fingerprint.lower()
    int(first_fingerprint, 16)
    assert service.public_key_fingerprint(second_public_key) != first_fingerprint
