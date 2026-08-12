# Project Scope

English | [简体中文](PROJECT_SCOPE.zh-CN.md)

## Final Product

A secure file encryption and sharing platform in which trusted clients create and retain
control of user private keys and file encryption keys. The backend stores client-encrypted
ciphertext, public keys, password-protected private-key envelopes, recipient-specific file-
key wrappings, access policy, recovery workflow state, and tamper-evident audit evidence.

## In Scope

- User registration, login, opaque server-side sessions, and role-based access control
- Separation of login password from the client-only encryption passphrase
- Client-generated RSA public/private key pairs
- Argon2id-derived KEK wrapping of a random account master key (AMK)
- AMK/HKDF-derived AES-256-GCM encryption of the PKCS#8 private-key bundle
- Client-side AES-256-GCM file encryption with independent random DEKs
- Bounded encrypted-ciphertext upload, storage, download, deletion, and SHA-256 integrity checks
- RSA-OAEP-SHA256 DEK wrapping for each authorized user
- Client-side DEK rewrapping for sharing, plus future-access revocation
- Key-protection profile retrieval and passphrase rewrap protected by optimistic revision plus
  newest-current-private-key RSA-PSS-SHA256 authorization
- Current-private-key-authorized successor key addition with historical bundles retained
- Recovery-public-key registration/rotation and mandatory upload recovery wrapping
- Time-bounded, maker-checker recovery requests with isolated offline/HSM DEK unwrap/rewrap
- Scoped audit queries and a serialized tamper-evident audit hash chain
- Administrative user/file listing and account enable/disable controls
- MySQL/Alembic schema delivery, production SQL parity, and readiness revision checks

## Out of Scope

- Recovery or server reset of a forgotten encryption passphrase
- Server-side decryption of user private keys, file DEKs, or file contents
- Metadata anonymity: filenames, MIME types, sizes, timestamps, ownership, and sharing graph
  are visible to the server in the current contract
- Protection from an actively malicious server without client fingerprint/revision pinning or
  an independent trust anchor
- Google Drive-style online document collaboration or real-time multi-user editing
- Large-scale cloud storage optimization or a performance guarantee for 1 GB+ files
- Forced deletion of ciphertext, DEKs, or plaintext already copied before revocation
- Encrypted full-text search, watermarking, and DRM/non-removable content controls
- Production-grade KMS/HSM implementation or automated offline-recovery workstation
- Forgotten-login-password reset, email verification, MFA, and external identity federation

## Core Limitations

The user normally needs to remember only the encryption passphrase because the encrypted
private-key bundle is stored by the service. If the passphrase is forgotten and no separately
secured backup/recovery factor exists, the AMK and that private key are cryptographically
unrecoverable. The implemented recovery workflow rewraps a file DEK to an already registered
active user public key; it does not recover the passphrase or private-key bundle.

Revocation controls future downloads through this platform. It cannot erase data already
obtained by a recipient.

The backend sees operational metadata and a stolen database permits offline guessing against
the Argon2id-protected key envelope. Strong passphrases and appropriately benchmarked KDF
parameters remain essential.

Recovery private keys are never submitted to the API. The repository implements the public-
key registration and governed request protocol, while real deployment must provide isolated
offline or HSM custody, operator authentication, clean-room logging rules, backup/rotation,
and tested disaster-recovery procedures.
