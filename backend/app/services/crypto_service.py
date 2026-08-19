from __future__ import annotations

import hashlib
import secrets
from dataclasses import replace
from uuid import UUID

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.security import PasswordManager
from app.domain.keys import (
    EncryptedPrivateKeyBundleInput,
    GeneratedAccountKey,
    KeyProtectionProfileInput,
)

SERVER_MANAGED_KEY_FORMAT_VERSION = 2
SERVER_MANAGED_KEY_AAD_VERSION = 1
SERVER_MANAGED_KDF_MEMORY_KIB = 65_536
SERVER_MANAGED_KDF_ITERATIONS = 3
SERVER_MANAGED_KDF_PARALLELISM = 4

_AES_KEY_BYTES = 32
_AES_GCM_NONCE_BYTES = 12
_AES_GCM_TAG_BYTES = 16
_SALT_BYTES = 16
_KEY_PROTECTION_AAD_DOMAIN = b"FYP-KEY-PROTECTION\x00"
_PRIVATE_KEY_AAD_DOMAIN = b"FYP-PRIVATE-KEY-BUNDLE\x00"
_PRIVATE_KEY_HKDF_DOMAIN = b"FYP-PRIVATE-KEY-DERIVATION\x00"


class CryptoService:
    """Low-level cryptographic operations.

    This class should only handle crypto primitives. Business logic such as
    access control, file metadata, and audit logging should stay in other services.
    """

    @staticmethod
    def key_protection_aad(
        *,
        profile_id: UUID,
        format_version: int,
        aad_version: int,
    ) -> bytes:
        """Build the public, cross-client AAD for the password-wrapped account key."""
        return (
            _KEY_PROTECTION_AAD_DOMAIN
            + format_version.to_bytes(4, "big")
            + aad_version.to_bytes(4, "big")
            + profile_id.bytes
        )

    @staticmethod
    def private_key_bundle_aad(
        *,
        key_id: UUID,
        profile_id: UUID,
        bundle_id: UUID,
        public_key_fingerprint: str,
        format_version: int,
        aad_version: int,
    ) -> bytes:
        """Build AAD binding a private-key ciphertext to its public identities."""
        return (
            _PRIVATE_KEY_AAD_DOMAIN
            + format_version.to_bytes(4, "big")
            + aad_version.to_bytes(4, "big")
            + profile_id.bytes
            + key_id.bytes
            + bundle_id.bytes
            + bytes.fromhex(public_key_fingerprint)
        )

    @staticmethod
    def private_key_derivation_info(
        *,
        key_id: UUID,
        profile_id: UUID,
        bundle_id: UUID,
        format_version: int,
    ) -> bytes:
        """Build the public HKDF context used for a private-key bundle."""
        return (
            _PRIVATE_KEY_HKDF_DOMAIN
            + format_version.to_bytes(4, "big")
            + profile_id.bytes
            + key_id.bytes
            + bundle_id.bytes
        )

    def generate_account_key(
        self,
        *,
        password: str,
        password_manager: PasswordManager,
        key_id: UUID,
        profile_id: UUID,
        bundle_id: UUID,
        key_size: int = 3072,
        kdf_memory_kib: int = SERVER_MANAGED_KDF_MEMORY_KIB,
        kdf_iterations: int = SERVER_MANAGED_KDF_ITERATIONS,
        kdf_parallelism: int = SERVER_MANAGED_KDF_PARALLELISM,
    ) -> GeneratedAccountKey:
        """Generate an RSA key pair and persistable login-password-wrapped envelopes."""
        if key_size not in {2048, 3072, 4096}:
            raise ValueError("RSA key size must be 2048, 3072, or 4096 bits")
        if not 65_536 <= kdf_memory_kib <= 1_048_576:
            raise ValueError("Argon2id memory cost is outside the supported range")
        if not 1 <= kdf_iterations <= 10:
            raise ValueError("Argon2id iterations are outside the supported range")
        if not 1 <= kdf_parallelism <= 16:
            raise ValueError("Argon2id parallelism is outside the supported range")

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        private_key_der = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )
        public_key_fingerprint = self.public_key_fingerprint(public_key_pem)

        profile_format_version = SERVER_MANAGED_KEY_FORMAT_VERSION
        profile_aad_version = SERVER_MANAGED_KEY_AAD_VERSION
        kdf_salt = secrets.token_bytes(_SALT_BYTES)
        password_key = password_manager.derive_argon2id_key(
            password,
            salt=kdf_salt,
            memory_cost_kib=kdf_memory_kib,
            iterations=kdf_iterations,
            parallelism=kdf_parallelism,
            length=_AES_KEY_BYTES,
        )
        account_master_key = secrets.token_bytes(_AES_KEY_BYTES)
        amk_nonce = secrets.token_bytes(_AES_GCM_NONCE_BYTES)
        wrapped_amk_and_tag = AESGCM(password_key).encrypt(
            amk_nonce,
            account_master_key,
            self.key_protection_aad(
                profile_id=profile_id,
                format_version=profile_format_version,
                aad_version=profile_aad_version,
            ),
        )
        wrapped_amk = wrapped_amk_and_tag[:-_AES_GCM_TAG_BYTES]
        amk_auth_tag = wrapped_amk_and_tag[-_AES_GCM_TAG_BYTES:]

        bundle_format_version = SERVER_MANAGED_KEY_FORMAT_VERSION
        bundle_aad_version = SERVER_MANAGED_KEY_AAD_VERSION
        derivation_salt = secrets.token_bytes(_SALT_BYTES)
        private_key_encryption_key = self._derive_private_key_encryption_key(
            account_master_key=account_master_key,
            derivation_salt=derivation_salt,
            key_id=key_id,
            profile_id=profile_id,
            bundle_id=bundle_id,
            format_version=bundle_format_version,
        )
        nonce = secrets.token_bytes(_AES_GCM_NONCE_BYTES)
        encrypted_private_key_and_tag = AESGCM(private_key_encryption_key).encrypt(
            nonce,
            private_key_der,
            self.private_key_bundle_aad(
                key_id=key_id,
                profile_id=profile_id,
                bundle_id=bundle_id,
                public_key_fingerprint=public_key_fingerprint,
                format_version=bundle_format_version,
                aad_version=bundle_aad_version,
            ),
        )
        encrypted_private_key = encrypted_private_key_and_tag[:-_AES_GCM_TAG_BYTES]
        auth_tag = encrypted_private_key_and_tag[-_AES_GCM_TAG_BYTES:]

        return GeneratedAccountKey(
            key_id=key_id,
            public_key_pem=public_key_pem,
            algorithm="RSA-OAEP-SHA256",
            key_size_bits=key_size,
            protection=KeyProtectionProfileInput(
                profile_id=profile_id,
                format_version=profile_format_version,
                kdf_algorithm="ARGON2ID",
                kdf_version=19,
                kdf_salt=kdf_salt,
                kdf_memory_kib=kdf_memory_kib,
                kdf_iterations=kdf_iterations,
                kdf_parallelism=kdf_parallelism,
                derived_key_length=_AES_KEY_BYTES,
                amk_wrapping_algorithm="AES-256-GCM",
                wrapped_amk=wrapped_amk,
                amk_nonce=amk_nonce,
                amk_auth_tag=amk_auth_tag,
                aad_version=profile_aad_version,
            ),
            private_key_bundle=EncryptedPrivateKeyBundleInput(
                bundle_id=bundle_id,
                format_version=bundle_format_version,
                private_key_format="PKCS8-DER",
                derivation_algorithm="HKDF-SHA256",
                derivation_salt=derivation_salt,
                encryption_algorithm="AES-256-GCM",
                encrypted_private_key=encrypted_private_key,
                nonce=nonce,
                auth_tag=auth_tag,
                aad_version=bundle_aad_version,
                ciphertext_sha256=hashlib.sha256(encrypted_private_key).hexdigest(),
            ),
        )

    def decrypt_account_private_key(
        self,
        *,
        password: str,
        password_manager: PasswordManager,
        registration: GeneratedAccountKey,
    ) -> rsa.RSAPrivateKey:
        """Decrypt and validate a generated private key; primarily used for verification."""
        protection = registration.protection
        bundle = registration.private_key_bundle
        try:
            self._validate_server_managed_registration(registration)
            account_master_key = self._unwrap_account_master_key(
                password=password,
                password_manager=password_manager,
                protection=protection,
            )
            private_key_encryption_key = self._derive_private_key_encryption_key(
                account_master_key=account_master_key,
                derivation_salt=bundle.derivation_salt,
                key_id=registration.key_id,
                profile_id=protection.profile_id,
                bundle_id=bundle.bundle_id,
                format_version=bundle.format_version,
            )
            public_key_fingerprint = self.public_key_fingerprint(registration.public_key_pem)
            private_key_der = AESGCM(private_key_encryption_key).decrypt(
                bundle.nonce,
                bundle.encrypted_private_key + bundle.auth_tag,
                self.private_key_bundle_aad(
                    key_id=registration.key_id,
                    profile_id=protection.profile_id,
                    bundle_id=bundle.bundle_id,
                    public_key_fingerprint=public_key_fingerprint,
                    format_version=bundle.format_version,
                    aad_version=bundle.aad_version,
                ),
            )
            private_key = serialization.load_der_private_key(private_key_der, password=None)
            if not isinstance(private_key, rsa.RSAPrivateKey):
                raise ValueError("The encrypted private key is not RSA")
            if private_key.key_size != registration.key_size_bits:
                raise ValueError("The encrypted private key size does not match its metadata")
            expected_public_key = self.load_rsa_public_key(
                registration.public_key_pem,
                expected_key_size=registration.key_size_bits,
            )
            if private_key.public_key().public_numbers() != expected_public_key.public_numbers():
                raise ValueError("The encrypted private key does not match the public key")
            return private_key
        except (InvalidTag, TypeError, ValueError) as exc:
            raise ValueError("The password or encrypted key material is invalid") from exc

    def rewrap_key_protection_profile(
        self,
        *,
        current_password: str,
        new_password: str,
        password_manager: PasswordManager,
        protection: KeyProtectionProfileInput,
    ) -> KeyProtectionProfileInput:
        """Rewrap the same AMK with a new login password and fresh salt/nonce."""
        self._validate_server_managed_protection(protection)
        account_master_key = self._unwrap_account_master_key(
            password=current_password,
            password_manager=password_manager,
            protection=protection,
        )
        new_salt = secrets.token_bytes(_SALT_BYTES)
        new_password_key = password_manager.derive_argon2id_key(
            new_password,
            salt=new_salt,
            memory_cost_kib=protection.kdf_memory_kib,
            iterations=protection.kdf_iterations,
            parallelism=protection.kdf_parallelism,
            length=protection.derived_key_length,
        )
        new_nonce = secrets.token_bytes(_AES_GCM_NONCE_BYTES)
        wrapped_amk_and_tag = AESGCM(new_password_key).encrypt(
            new_nonce,
            account_master_key,
            self.key_protection_aad(
                profile_id=protection.profile_id,
                format_version=protection.format_version,
                aad_version=protection.aad_version,
            ),
        )
        return replace(
            protection,
            kdf_salt=new_salt,
            wrapped_amk=wrapped_amk_and_tag[:-_AES_GCM_TAG_BYTES],
            amk_nonce=new_nonce,
            amk_auth_tag=wrapped_amk_and_tag[-_AES_GCM_TAG_BYTES:],
        )

    def _unwrap_account_master_key(
        self,
        *,
        password: str,
        password_manager: PasswordManager,
        protection: KeyProtectionProfileInput,
    ) -> bytes:
        self._validate_server_managed_protection(protection)
        password_key = password_manager.derive_argon2id_key(
            password,
            salt=protection.kdf_salt,
            memory_cost_kib=protection.kdf_memory_kib,
            iterations=protection.kdf_iterations,
            parallelism=protection.kdf_parallelism,
            length=protection.derived_key_length,
        )
        try:
            return AESGCM(password_key).decrypt(
                protection.amk_nonce,
                protection.wrapped_amk + protection.amk_auth_tag,
                self.key_protection_aad(
                    profile_id=protection.profile_id,
                    format_version=protection.format_version,
                    aad_version=protection.aad_version,
                ),
            )
        except InvalidTag as exc:
            raise ValueError("The password or key-protection envelope is invalid") from exc

    def _derive_private_key_encryption_key(
        self,
        *,
        account_master_key: bytes,
        derivation_salt: bytes,
        key_id: UUID,
        profile_id: UUID,
        bundle_id: UUID,
        format_version: int,
    ) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=_AES_KEY_BYTES,
            salt=derivation_salt,
            info=self.private_key_derivation_info(
                key_id=key_id,
                profile_id=profile_id,
                bundle_id=bundle_id,
                format_version=format_version,
            ),
        ).derive(account_master_key)

    @staticmethod
    def _validate_server_managed_protection(protection: KeyProtectionProfileInput) -> None:
        if protection.format_version != SERVER_MANAGED_KEY_FORMAT_VERSION:
            raise ValueError("The key-protection profile is not login-password-bound")
        if (
            protection.kdf_algorithm != "ARGON2ID"
            or protection.kdf_version != 19
            or protection.derived_key_length != _AES_KEY_BYTES
            or protection.amk_wrapping_algorithm != "AES-256-GCM"
            or protection.aad_version != SERVER_MANAGED_KEY_AAD_VERSION
        ):
            raise ValueError("The key-protection profile uses an unsupported suite")
        if not 16 <= len(protection.kdf_salt) <= 32:
            raise ValueError("The key-protection salt has an invalid length")
        if not 65_536 <= protection.kdf_memory_kib <= 1_048_576:
            raise ValueError("The key-protection memory cost is outside the supported range")
        if not 1 <= protection.kdf_iterations <= 10:
            raise ValueError("The key-protection iterations are outside the supported range")
        if not 1 <= protection.kdf_parallelism <= 16:
            raise ValueError("The key-protection parallelism is outside the supported range")
        if len(protection.amk_nonce) != _AES_GCM_NONCE_BYTES:
            raise ValueError("The wrapped AMK nonce has an invalid length")
        if len(protection.wrapped_amk) != _AES_KEY_BYTES:
            raise ValueError("The wrapped AMK has an invalid length")
        if len(protection.amk_auth_tag) != _AES_GCM_TAG_BYTES:
            raise ValueError("The wrapped AMK authentication tag has an invalid length")

    @staticmethod
    def _validate_server_managed_registration(registration: GeneratedAccountKey) -> None:
        bundle = registration.private_key_bundle
        if registration.algorithm != "RSA-OAEP-SHA256":
            raise ValueError("The public key uses an unsupported algorithm")
        if bundle.format_version != SERVER_MANAGED_KEY_FORMAT_VERSION:
            raise ValueError("The private-key bundle is not login-password-bound")
        if (
            bundle.private_key_format != "PKCS8-DER"
            or bundle.derivation_algorithm != "HKDF-SHA256"
            or bundle.encryption_algorithm != "AES-256-GCM"
            or bundle.aad_version != SERVER_MANAGED_KEY_AAD_VERSION
        ):
            raise ValueError("The private-key bundle uses an unsupported suite")
        if not 16 <= len(bundle.derivation_salt) <= 32:
            raise ValueError("The private-key derivation salt has an invalid length")
        if len(bundle.nonce) != _AES_GCM_NONCE_BYTES:
            raise ValueError("The private-key nonce has an invalid length")
        if len(bundle.auth_tag) != _AES_GCM_TAG_BYTES:
            raise ValueError("The private-key authentication tag has an invalid length")
        if not 256 <= len(bundle.encrypted_private_key) <= 8192:
            raise ValueError("The encrypted private key has an invalid length")
        if hashlib.sha256(bundle.encrypted_private_key).hexdigest() != bundle.ciphertext_sha256:
            raise ValueError("The encrypted private-key digest does not match")

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
