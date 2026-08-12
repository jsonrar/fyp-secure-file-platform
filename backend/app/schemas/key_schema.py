from __future__ import annotations

import base64
import binascii
import hashlib
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.domain.keys import (
    ClientKeyAddition,
    ClientKeyRegistration,
    EncryptedPrivateKeyBundleInput,
    KeyProtectionProfileInput,
)

Base64Value = Annotated[str, StringConstraints(min_length=4, max_length=12000)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def decode_base64(value: str, *, field_name: str, exact_length: int | None = None) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field_name} must be canonical base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{field_name} must be canonical base64")
    if exact_length is not None and len(decoded) != exact_length:
        raise ValueError(f"{field_name} must decode to exactly {exact_length} bytes")
    return decoded


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KeyProtectionProfileIn(_StrictModel):
    profile_id: UUID
    format_version: Literal[1] = 1
    kdf_algorithm: Literal["ARGON2ID"] = "ARGON2ID"
    kdf_version: Literal[19] = 19
    kdf_salt: Base64Value
    kdf_memory_kib: int = Field(ge=65_536, le=1_048_576)
    kdf_iterations: int = Field(ge=1, le=10)
    kdf_parallelism: int = Field(ge=1, le=16)
    derived_key_length: Literal[32] = 32
    amk_wrapping_algorithm: Literal["AES-256-GCM"] = "AES-256-GCM"
    wrapped_amk: Base64Value
    amk_nonce: Base64Value
    amk_auth_tag: Base64Value
    aad_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_binary_fields(self) -> KeyProtectionProfileIn:
        salt = decode_base64(self.kdf_salt, field_name="kdf_salt")
        if not 16 <= len(salt) <= 32:
            raise ValueError("kdf_salt must decode to between 16 and 32 bytes")
        decode_base64(self.wrapped_amk, field_name="wrapped_amk", exact_length=32)
        decode_base64(self.amk_nonce, field_name="amk_nonce", exact_length=12)
        decode_base64(self.amk_auth_tag, field_name="amk_auth_tag", exact_length=16)
        return self

    def to_domain(self) -> KeyProtectionProfileInput:
        return KeyProtectionProfileInput(
            profile_id=self.profile_id,
            format_version=self.format_version,
            kdf_algorithm=self.kdf_algorithm,
            kdf_version=self.kdf_version,
            kdf_salt=decode_base64(self.kdf_salt, field_name="kdf_salt"),
            kdf_memory_kib=self.kdf_memory_kib,
            kdf_iterations=self.kdf_iterations,
            kdf_parallelism=self.kdf_parallelism,
            derived_key_length=self.derived_key_length,
            amk_wrapping_algorithm=self.amk_wrapping_algorithm,
            wrapped_amk=decode_base64(self.wrapped_amk, field_name="wrapped_amk"),
            amk_nonce=decode_base64(self.amk_nonce, field_name="amk_nonce"),
            amk_auth_tag=decode_base64(self.amk_auth_tag, field_name="amk_auth_tag"),
            aad_version=self.aad_version,
        )


class EncryptedPrivateKeyBundleIn(_StrictModel):
    bundle_id: UUID
    format_version: Literal[1] = 1
    private_key_format: Literal["PKCS8-DER"] = "PKCS8-DER"
    derivation_algorithm: Literal["HKDF-SHA256"] = "HKDF-SHA256"
    derivation_salt: Base64Value
    encryption_algorithm: Literal["AES-256-GCM"] = "AES-256-GCM"
    encrypted_private_key: Base64Value
    nonce: Base64Value
    auth_tag: Base64Value
    aad_version: Literal[1] = 1
    ciphertext_sha256: Sha256Hex

    @model_validator(mode="after")
    def validate_binary_fields(self) -> EncryptedPrivateKeyBundleIn:
        salt = decode_base64(self.derivation_salt, field_name="derivation_salt")
        if not 16 <= len(salt) <= 32:
            raise ValueError("derivation_salt must decode to between 16 and 32 bytes")
        ciphertext = decode_base64(self.encrypted_private_key, field_name="encrypted_private_key")
        if not 256 <= len(ciphertext) <= 8192:
            raise ValueError("encrypted_private_key has an invalid decoded length")
        decode_base64(self.nonce, field_name="nonce", exact_length=12)
        decode_base64(self.auth_tag, field_name="auth_tag", exact_length=16)
        if not hashlib.sha256(ciphertext).hexdigest() == self.ciphertext_sha256:
            raise ValueError("ciphertext_sha256 does not match encrypted_private_key")
        return self

    def to_domain(self) -> EncryptedPrivateKeyBundleInput:
        return EncryptedPrivateKeyBundleInput(
            bundle_id=self.bundle_id,
            format_version=self.format_version,
            private_key_format=self.private_key_format,
            derivation_algorithm=self.derivation_algorithm,
            derivation_salt=decode_base64(self.derivation_salt, field_name="derivation_salt"),
            encryption_algorithm=self.encryption_algorithm,
            encrypted_private_key=decode_base64(
                self.encrypted_private_key, field_name="encrypted_private_key"
            ),
            nonce=decode_base64(self.nonce, field_name="nonce"),
            auth_tag=decode_base64(self.auth_tag, field_name="auth_tag"),
            aad_version=self.aad_version,
            ciphertext_sha256=self.ciphertext_sha256,
        )


class ClientKeyRegistrationIn(_StrictModel):
    key_id: UUID
    public_key_pem: str = Field(min_length=200, max_length=8000)
    algorithm: Literal["RSA-OAEP-SHA256"] = "RSA-OAEP-SHA256"
    key_size_bits: Literal[2048, 3072, 4096] = 3072
    protection: KeyProtectionProfileIn
    private_key_bundle: EncryptedPrivateKeyBundleIn

    @field_validator("public_key_pem")
    @classmethod
    def reject_padded_public_key(cls, value: str) -> str:
        normalized = value.strip()
        if "PRIVATE KEY" in normalized:
            raise ValueError("public_key_pem must contain only a public key")
        return f"{normalized}\n"

    def to_domain(self) -> ClientKeyRegistration:
        return ClientKeyRegistration(
            key_id=self.key_id,
            public_key_pem=self.public_key_pem,
            algorithm=self.algorithm,
            key_size_bits=self.key_size_bits,
            protection=self.protection.to_domain(),
            private_key_bundle=self.private_key_bundle.to_domain(),
        )


class ClientKeyAdditionIn(_StrictModel):
    """Unsigned key-addition fields covered by the current-key authorization signature."""

    authorizing_key_id: UUID
    protection_profile_id: UUID
    expected_profile_revision: int = Field(ge=1)
    key_id: UUID
    public_key_pem: str = Field(min_length=200, max_length=8000)
    algorithm: Literal["RSA-OAEP-SHA256"] = "RSA-OAEP-SHA256"
    key_size_bits: Literal[2048, 3072, 4096] = 3072
    private_key_bundle: EncryptedPrivateKeyBundleIn

    @field_validator("public_key_pem")
    @classmethod
    def require_public_key_only(cls, value: str) -> str:
        normalized = value.strip()
        if "PRIVATE KEY" in normalized:
            raise ValueError("public_key_pem must contain only a public key")
        return f"{normalized}\n"

    def to_domain(self) -> ClientKeyAddition:
        return ClientKeyAddition(
            authorizing_key_id=self.authorizing_key_id,
            protection_profile_id=self.protection_profile_id,
            expected_profile_revision=self.expected_profile_revision,
            key_id=self.key_id,
            public_key_pem=self.public_key_pem,
            algorithm=self.algorithm,
            key_size_bits=self.key_size_bits,
            private_key_bundle=self.private_key_bundle.to_domain(),
        )


class AddClientKeyRequest(ClientKeyAdditionIn):
    authorization_algorithm: Literal["RSA-PSS-SHA256"] = "RSA-PSS-SHA256"
    authorization_signature: Base64Value = Field(repr=False)

    @field_validator("authorization_signature")
    @classmethod
    def validate_authorization_signature(cls, value: str) -> str:
        signature = decode_base64(value, field_name="authorization_signature")
        if len(signature) not in {256, 384, 512}:
            raise ValueError("authorization_signature must be an RSA signature")
        return value

    def signature_bytes(self) -> bytes:
        return decode_base64(
            self.authorization_signature,
            field_name="authorization_signature",
        )


class KeyAdditionSigningPayloadOut(_StrictModel):
    authorization_algorithm: Literal["RSA-PSS-SHA256"] = "RSA-PSS-SHA256"
    authorization_payload: str = Field(repr=False)


class AddClientKeyResponse(_StrictModel):
    key_id: UUID
    bundle_id: UUID
    protection_profile_id: UUID
    protection_revision: int = Field(ge=1)
    public_key_fingerprint: Sha256Hex
    created_at: datetime
    previous_keys_retained: Literal[True] = True


class KeyProtectionProfileOut(_StrictModel):
    profile_id: UUID
    format_version: int
    kdf_algorithm: str
    kdf_version: int
    kdf_salt: str
    kdf_memory_kib: int
    kdf_iterations: int
    kdf_parallelism: int
    derived_key_length: int
    amk_wrapping_algorithm: str
    wrapped_amk: str
    amk_nonce: str
    amk_auth_tag: str
    aad_version: int
    revision: int
    updated_at: datetime


class EncryptedPrivateKeyBundleOut(_StrictModel):
    bundle_id: UUID
    format_version: int
    private_key_format: str
    derivation_algorithm: str
    derivation_salt: str
    encryption_algorithm: str
    encrypted_private_key: str
    nonce: str
    auth_tag: str
    aad_version: int
    ciphertext_sha256: str
    revision: int
    updated_at: datetime


class PublicEncryptionKeyOut(_StrictModel):
    key_id: UUID
    user_id: UUID
    algorithm: str
    key_size_bits: int
    public_key_pem: str
    fingerprint: str
    created_at: datetime


class MyKeyBundleResponse(_StrictModel):
    key: PublicEncryptionKeyOut
    protection: KeyProtectionProfileOut
    private_key_bundle: EncryptedPrivateKeyBundleOut


class RewrapKeyProtectionIn(KeyProtectionProfileIn):
    authorizing_key_id: UUID
    expected_revision: int = Field(ge=1)


class RewrapKeyProtectionRequest(RewrapKeyProtectionIn):
    authorization_algorithm: Literal["RSA-PSS-SHA256"] = "RSA-PSS-SHA256"
    authorization_signature: Base64Value = Field(repr=False)

    @field_validator("authorization_signature")
    @classmethod
    def validate_authorization_signature(cls, value: str) -> str:
        signature = decode_base64(value, field_name="authorization_signature")
        if len(signature) not in {256, 384, 512}:
            raise ValueError("authorization_signature must be an RSA signature")
        return value

    def signature_bytes(self) -> bytes:
        return decode_base64(
            self.authorization_signature,
            field_name="authorization_signature",
        )


class RewrapKeyProtectionSigningPayloadOut(_StrictModel):
    authorization_algorithm: Literal["RSA-PSS-SHA256"] = "RSA-PSS-SHA256"
    authorization_payload: str = Field(repr=False)


class RewrapKeyProtectionResponse(_StrictModel):
    profile_id: UUID
    revision: int
    updated_at: datetime


def encode_base64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def first_attr(value: Any, *names: str) -> Any:
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    raise AttributeError(f"None of {names!r} exist")
