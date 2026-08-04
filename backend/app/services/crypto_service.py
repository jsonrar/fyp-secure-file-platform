import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class EncryptionResult:
    ciphertext: bytes
    file_key: bytes
    iv: bytes
    auth_tag: bytes


class CryptoService:
    """Low-level cryptographic operations.

    This class should only handle crypto primitives. Business logic such as
    access control, file metadata, and audit logging should stay in other services.
    """

    AES_KEY_SIZE = 32
    AES_GCM_IV_SIZE = 12
    AES_GCM_TAG_SIZE = 16

    def generate_aes_key(self) -> bytes:
        return os.urandom(self.AES_KEY_SIZE)

    def encrypt_bytes(self, plaintext: bytes) -> EncryptionResult:
        file_key = self.generate_aes_key()
        iv = os.urandom(self.AES_GCM_IV_SIZE)
        aesgcm = AESGCM(file_key)
        encrypted = aesgcm.encrypt(iv, plaintext, associated_data=None)
        ciphertext = encrypted[: -self.AES_GCM_TAG_SIZE]
        auth_tag = encrypted[-self.AES_GCM_TAG_SIZE :]
        return EncryptionResult(ciphertext=ciphertext, file_key=file_key, iv=iv, auth_tag=auth_tag)

    def decrypt_bytes(
        self, ciphertext: bytes, file_key: bytes, iv: bytes, auth_tag: bytes
    ) -> bytes:
        aesgcm = AESGCM(file_key)
        return aesgcm.decrypt(iv, ciphertext + auth_tag, associated_data=None)

    def generate_rsa_key_pair(self, key_size: int = 3072) -> tuple[str, str]:
        if key_size < 2048:
            raise ValueError("RSA keys must be at least 2048 bits")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return private_pem, public_pem

    def public_key_fingerprint(self, public_key_pem: str) -> str:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
            raise ValueError("A supported RSA public key of at least 2048 bits is required")
        canonical_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(canonical_der).hexdigest()

    def wrap_file_key(self, file_key: bytes, public_key_pem: str) -> bytes:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
            raise ValueError("A supported RSA public key of at least 2048 bits is required")
        return public_key.encrypt(
            file_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def unwrap_file_key(self, wrapped_file_key: bytes, private_key_pem: str) -> bytes:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
        if not isinstance(private_key, rsa.RSAPrivateKey) or private_key.key_size < 2048:
            raise ValueError("A supported RSA private key of at least 2048 bits is required")
        return private_key.decrypt(
            wrapped_file_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
