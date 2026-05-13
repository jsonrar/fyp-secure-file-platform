# Project Scope

## Final Product

A secure file encryption and sharing platform that protects uploaded files using server-side AES encryption, manages file access through RSA-based key wrapping, supports controlled sharing and revocation, and strengthens accountability through integrity verification, recovery governance, and tamper-evident audit logs.

## In Scope

- User registration and login
- Role-based access control
- File upload
- Server-side AES encryption
- Encrypted file storage
- File metadata management
- RSA public/private key pair generation for users
- AES file key wrapping for each authorised user
- File sharing with selected users
- Access revocation for future downloads
- SHA-256 encrypted file integrity verification
- Audit logging for security-sensitive operations
- Tamper-evident audit log hash chain
- Recovery key mechanism for exceptional access
- Basic admin dashboard

## Out of Scope

- Full end-to-end encryption
- Google Drive-style online document collaboration
- Real-time multi-user editing
- Large-scale cloud storage optimisation
- Performance guarantee for very large files, such as 1GB+
- Forced deletion of files already downloaded before revocation
- Fully non-removable watermarking
- Encrypted full-text search
- Production-grade KMS/HSM integration

## Core Limitations

Revocation only prevents future access through the platform. If a user has already downloaded a plaintext copy before revocation, the system cannot delete that local copy.

Watermarking is used for deterrence and traceability. It cannot fully prevent screenshots, photos, file conversion, or deliberate removal.

The recovery mechanism is included for FYP demonstration and governance discussion. In production, recovery private keys should be protected using stronger operational controls.
