# Architecture Design

## Architectural Style

The project uses a modular monolithic architecture.

This is suitable for the FYP because the system can be developed and demonstrated as one application while still keeping clear internal module boundaries.

## High-Level Architecture

```text
Frontend Web App
    ↓ HTTPS / REST API
Backend API Server
    ↓
Service Layer
    ↓
MySQL Database + Encrypted File Storage
```

## Backend Layers

```text
Router Layer
    Receives HTTP requests, validates basic input, returns API responses.

Service Layer
    Contains business logic such as encryption, sharing, access control, recovery, and audit logging.

Model Layer
    Defines SQLAlchemy ORM models.

Data Layer
    Stores metadata in MySQL and encrypted files in local storage.
```

## Main Backend Modules

| Module | Responsibility |
|---|---|
| AuthService | Registration, login, password verification, session/token handling |
| UserService | User profile, role assignment, public key management |
| FileService | File upload, metadata, download orchestration |
| CryptoService | AES encryption/decryption and RSA key wrapping |
| KeyService | User public key lookup and file key wrapping records |
| SharingService | Share and revoke access |
| AccessControlService | Checks file-level permissions |
| IntegrityService | SHA-256 verification |
| AuditLogService | Records operations and maintains hash chain |
| RecoveryService | Handles recovery request, approval, and execution |
| WatermarkService | Adds optional download watermark where supported |

## Security Architecture

Each uploaded file receives a unique AES file key.

The file content is encrypted using AES-256-GCM. The AES key is not stored directly. Instead, it is wrapped using RSA-OAEP for each authorised user.

```text
AES File Key
 ├── wrapped using owner public key
 ├── wrapped using shared user's public key
 └── wrapped using recovery public key
```

Access requires two conditions:

1. The database permission says the user is authorised.
2. The user has an active wrapped file key entry.

This design combines normal access control with cryptographic access control.
