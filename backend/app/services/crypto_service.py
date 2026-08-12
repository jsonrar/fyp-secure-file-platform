import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class CryptoService:
    """Low-level cryptographic operations.

    This class should only handle crypto primitives. Business logic such as
    access control, file metadata, and audit logging should stay in other services.
    """

    def public_key_fingerprint(self, public_key_pem: str) -> str:
        public_key = self.load_rsa_public_key(public_key_pem)
        canonical_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(canonical_der).hexdigest()

    def load_rsa_public_key(
        self,
        public_key_pem: str,
        *,
        expected_key_size: int | None = None,
    ) -> rsa.RSAPublicKey:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
            raise ValueError("A supported RSA public key of at least 2048 bits is required")
        if public_key.public_numbers().e != 65537:
            raise ValueError("RSA public exponent 65537 is required")
        if expected_key_size is not None and public_key.key_size != expected_key_size:
            raise ValueError("RSA public key size does not match the declared key size")
        return public_key

    def validate_wrapped_file_key(
        self,
        wrapped_file_key: bytes,
        public_key_pem: str,
    ) -> None:
        public_key = self.load_rsa_public_key(public_key_pem)
        if len(wrapped_file_key) != public_key.key_size // 8:
            raise ValueError("Wrapped file key length does not match the recipient RSA key")

    def verify_rsa_pss_sha256_signature(
        self,
        *,
        public_key_pem: str,
        message: bytes,
        signature: bytes,
    ) -> None:
        public_key = self.load_rsa_public_key(public_key_pem)
        if len(signature) != public_key.key_size // 8:
            raise ValueError("RSA signature length does not match the authorizing key")
        try:
            public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=hashes.SHA256.digest_size,
                ),
                hashes.SHA256(),
            )
        except InvalidSignature as exc:
            raise ValueError("RSA-PSS authorization signature is invalid") from exc
