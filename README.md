# Secure File Encryption and Sharing Platform

Final Year Project architecture for a secure file encryption and sharing platform.

## Project Goal

This system allows users to upload files, store them encrypted on the server, share files
with other authorised users, revoke future access, verify file integrity, and record
security-sensitive actions in a tamper-evident audit log.

The project focuses on:

- Server-side AES file encryption
- RSA-based file-key wrapping
- Controlled sharing and revocation
- Role-based and file-level access control
- SHA-256 integrity verification
- Tamper-evident audit-log hash chaining
- Recovery governance for exceptional access cases

## Current Status

The backend authentication vertical slice is implemented with persistent accounts, opaque
access tokens, rotating one-time refresh tokens, revocable sessions, password changes,
database-backed throttling, RSA registration keys, and transactionally appended audit
events. The nine Auth endpoints are documented in
[API_DESIGN.md](docs/API_DESIGN.md#auth-api).

File, sharing, audit-query, recovery, and admin business APIs remain visible in OpenAPI but
deliberately return `501 feature_not_implemented`. They will be enabled one vertical slice
at a time after their authorization, transaction, audit, storage, and denial tests exist.

Backend Auth readiness does not make the current frontend login flow production-ready: its
page still contains a prototype credential bypass/token fallback that must be removed before
end-to-end authentication testing or deployment.

## Recommended Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | FastAPI |
| Database | MySQL 8.4 |
| File Storage | Local encrypted file storage for the FYP demo |
| File Encryption | AES-256-GCM |
| Key Wrapping | RSA-OAEP with SHA-256 |
| Password Hashing | Argon2id (`pwdlib`) |

## Repository Structure

```text
fyp-secure-file-platform/
|-- backend/
|   |-- app/
|   |   |-- api/v1/routers/
|   |   |-- core/
|   |   |-- domain/
|   |   |-- models/
|   |   |-- repositories/
|   |   |-- schemas/
|   |   `-- services/
|   |-- migrations/
|   |-- scripts/
|   |-- tests/
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   `-- package.json
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- API_DESIGN.md
|   |-- DATABASE_SCHEMA.md
|   |-- DEPLOYMENT.md
|   |-- SECURITY_FLOWS.md
|   `-- PROJECT_SCOPE.md
|-- .env.example
|-- .gitignore
`-- docker-compose.yml
```

## Local Setup

Auth endpoints are operational. Other business endpoints remain fail-closed with
`501 feature_not_implemented`; health and OpenAPI are also available.

### Backend

Before running the migration command below, confirm that the target is clean or already has
an `alembic_version` row. The currently inspected local legacy database does not; skip the
normal upgrade and follow the adoption warning below if that database is still present.

```bash
docker compose up -d mysql
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`alembic upgrade head` is safe for a clean database or one already managed by this Alembic
history. A local database created by the former `docs/init.sql` must not be blindly upgraded
or stamped; follow [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md#adopting-a-legacy-development-database).

### MySQL deployment

Production and staging releases use the guarded scripts in `backend/scripts/`. They provision
separate runtime and migration accounts, serialize migrations with a MySQL advisory lock,
refuse unmanaged legacy schemas, run Alembic to head, and verify metadata drift.

```bash
cd backend
python -m scripts.provision_mysql       # first deployment only; requires admin variables
python -m scripts.deploy_mysql          # clean database
python -m scripts.deploy_mysql --confirm-backup  # managed database that needs an upgrade
python -m scripts.verify_mysql
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for required secret variables, account grants,
backup requirements, release order, and rollback guidance. The deployment scripts require
MySQL 8.4 with strict SQL mode; they never drop, reset, or stamp an unmanaged database.

OpenAPI: <http://localhost:8000/docs>

Run backend quality checks from `backend/`:

```bash
ruff format --check app tests migrations scripts
ruff check app tests migrations scripts
pytest
alembic check
pip-audit -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: <http://localhost:5173>

## Important Security Note

This remains an FYP prototype. Its built-in password deny-list is deliberately small and is
not a maintained breached-password corpus. Forgotten-password recovery, email verification,
MFA, and external identity providers also require trusted out-of-band services and are not
implemented. A production deployment additionally needs stronger key custody through a
KMS/HSM, hardened operations, externally anchored audit checkpoints, and professional
security review.
