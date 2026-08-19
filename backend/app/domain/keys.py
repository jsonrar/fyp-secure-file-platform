from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class KeyProtectionProfileInput:
    profile_id: UUID
    format_version: int
    kdf_algorithm: str
    kdf_version: int
    kdf_salt: bytes = field(repr=False)
    kdf_memory_kib: int
    kdf_iterations: int
    kdf_parallelism: int
    derived_key_length: int
    amk_wrapping_algorithm: str
    wrapped_amk: bytes = field(repr=False)
    amk_nonce: bytes = field(repr=False)
    amk_auth_tag: bytes = field(repr=False)
    aad_version: int


@dataclass(frozen=True, slots=True)
class EncryptedPrivateKeyBundleInput:
    bundle_id: UUID
    format_version: int
    private_key_format: str
    derivation_algorithm: str
    derivation_salt: bytes = field(repr=False)
    encryption_algorithm: str
    encrypted_private_key: bytes = field(repr=False)
    nonce: bytes = field(repr=False)
    auth_tag: bytes = field(repr=False)
    aad_version: int
    ciphertext_sha256: str


@dataclass(frozen=True, slots=True)
class GeneratedAccountKey:
    key_id: UUID
    public_key_pem: str
    algorithm: str
    key_size_bits: int
    protection: KeyProtectionProfileInput = field(repr=False)
    private_key_bundle: EncryptedPrivateKeyBundleInput = field(repr=False)


@dataclass(frozen=True, slots=True)
class ClientKeyAddition:
    """A new key encrypted under the account's existing AMK protection profile."""

    authorizing_key_id: UUID
    protection_profile_id: UUID
    expected_profile_revision: int
    key_id: UUID
    public_key_pem: str
    algorithm: str
    key_size_bits: int
    private_key_bundle: EncryptedPrivateKeyBundleInput = field(repr=False)
