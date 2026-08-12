import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.services.crypto_service import CryptoService


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
