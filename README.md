# Secure File Encryption and Sharing Platform

[English](README.md) | [简体中文](README.zh-CN.md)

Final Year Project architecture for a secure file encryption and sharing platform.

## Staging Deployment

The current build runs at **https://secureview.tech**. The live API can be inspected and
demonstrated in [Swagger UI](https://secureview.tech/docs); the machine-readable contract is
at [OpenAPI JSON](https://secureview.tech/openapi.json).

Always write and share the URL **with the `https://` prefix**. `.tech` is not on the browser
HSTS preload list, so a visitor who types the bare domain reaches `http://` once before the
redirect, and some in-app browsers (WeChat among them) warn during that hop. After one HTTPS
visit the `Strict-Transport-Security` header pins the scheme for a year.

HTTPS is required for the product to work at all, not only for the padlock: the browser
exposes `crypto.subtle` only in a secure context, and registration uses it to generate the
account RSA key pair and derive the Argon2id key-encryption key.

## Project Goal

This system allows users to upload files, store them encrypted on the server, share files
with other authorised users, revoke future access, verify file integrity, and record
security-sensitive actions in a tamper-evident audit log.

The project focuses on:

- Client-side AES-GCM (128/192/256-bit keys) and ChaCha20-Poly1305 file encryption
- RSA-based file-key wrapping
- Controlled sharing and revocation
- Role-based and file-level access control
- SHA-256 integrity verification
- Tamper-evident audit-log hash chaining
- Recovery governance for exceptional access cases

## Current Status

The backend Auth, client-wrapped key custody, encrypted-file, sharing, audit-query,
offline-governed recovery, and admin/RBAC APIs are implemented. The server persists only
public keys, encrypted private-key bundles, ciphertext, and wrapped file keys; a user's
vault passphrase, KEK, AMK, plaintext private key, file DEK, and plaintext file never belong
in an API request or database row. Registration and file/key flows are documented in
[SECURITY_FLOWS.md](docs/SECURITY_FLOWS.md).

The browser MVP is operational end to end: emailed-code registration and password reset,
client-held account-key enrolment, passphrase or private-key-file unlock, idle relock,
authenticated encryption before upload, local decryption after download, filename search,
sharing by rewrapping the file key to the recipient, revocation, per-file access history,
silent session refresh, logout, and account deletion. AES-128/192/256-GCM and
ChaCha20-Poly1305 are selectable per file; AES-256-GCM remains the default. The former
hard-coded credential and demo-token fallbacks are gone.

The remaining work is production hardening rather than an unfinished basic demo: required CI
and MySQL 8.4 gates, passphrase-change and successor-key UI, complete admin/recovery-officer
screens, encrypted off-server backup/restore drills, scheduled reconciliation, observability,
and formal security review. The prioritized summary is in [TODO.md](TODO.md), and executable
work with acceptance criteria is tracked in [GitHub Issues](https://github.com/jsonrar/fyp-secure-file-platform/issues).

## HTTP Method Policy

Application APIs use only `GET` and `POST`. `GET` is reserved for read-only operations;
creation, updates, deletion, revocation, and all other state-changing actions use `POST`.
Action endpoints use explicit paths where appropriate, such as
`POST /api/v1/files/{file_id}/delete` and
`POST /api/v1/auth/sessions/{session_id}/revoke`. Application routes and clients must not
use `PUT`, `PATCH`, or `DELETE`, and CORS allows only `GET` and `POST` methods.
Automatic protocol-level handling required by browsers or servers (such as CORS preflight)
is infrastructure behavior rather than an application API operation.

## Recommended Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | FastAPI |
| Database | MySQL 8.4 |
| File Storage | Local encrypted file storage for the FYP demo |
| File Encryption | AES-128/192/256-GCM and ChaCha20-Poly1305 (default: AES-256-GCM) |
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
|   |-- tests/
|   `-- requirements.txt
|-- database/
|   `-- mysql/
|       |-- 01-provision.sql
|       |-- 02-schema.sql
|       `-- 03-verify.sql
|-- deployment/
|   `-- server/
|       |-- mcs21-deploy
|       |-- mcs21-auto-deploy
|       |-- mcs21-auto-deploy.service
|       `-- mcs21-auto-deploy.timer
|-- frontend/
|   |-- src/
|   `-- package.json
|-- changelog/
|   |-- CHANGELOG.md
|   |-- README.md
|   `-- work-packages/
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- API_DESIGN.md
|   |-- DATABASE_SCHEMA.md
|   |-- DEPLOYMENT.md
|   |-- AUTOMATIC_DEPLOYMENT.md
|   |-- SECURITY_FLOWS.md
|   `-- PROJECT_SCOPE.md
|-- .env.example
|-- .gitignore
`-- docker-compose.yml
```

## Change Log

Everything the team has changed, and why, is recorded in
[`changelog/CHANGELOG.md`](changelog/CHANGELOG.md). Per-work-package records live in
[`changelog/work-packages/`](changelog/work-packages/). Read
[`changelog/README.md`](changelog/README.md) before adding an entry: it says which of the two
a given entry belongs in.

## Team Workflow and Sources of Truth

- `changelog/CHANGELOG.md`: what shipped and why it mattered.
- GitHub Issues: executable remaining work, ownership, discussion, and acceptance criteria.
- `TODO.md`: prioritized summary linked to those Issues, not a second independent backlog.
- `README.md`: current user-facing capabilities, setup, and deployment entry points.

Every pull request must review all four, update the affected records, and explain any
intentional `N/A`. Runtime changes are not complete at merge: after `main` deploys, record the
deployed SHA and verify health plus the changed user-visible path. The repository pull-request
template carries this checklist.

## Local Setup

All backend business routers are operational. Health, readiness, and OpenAPI are available;
protected routes require bearer authentication and the admin/recovery routes enforce RBAC.

### Backend

Before running the migration command below, confirm that the target is clean or already has
an `alembic_version` row. The currently inspected local legacy database does not; skip the
normal upgrade and follow the adoption warning below if that database is still present.

```bash
docker compose up -d --wait mysql
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

The Alembic command above is a local-development and CI authoring workflow only. It is safe
for a clean development database or one already managed by this Alembic history. A local
database created by the historical, now-deleted `docs/init.sql` must not be blindly upgraded
or stamped; follow
[DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md#adopting-a-legacy-development-database).

Compose creates the configured database and `DB_USER` only when initializing a fresh local
volume. That account is a development convenience and does not reproduce the table-scoped,
least-privilege runtime policy required for staging or production.

### MySQL deployment

Production and staging use three reviewed SQL files. A MySQL root/administrator executes all
three in fail-fast batch mode from the repository root on the database server; production
does not install or run Alembic:

```bash
sudo mysql < database/mysql/01-provision.sql
sudo mysql < database/mysql/02-schema.sql
sudo mysql < database/mysql/03-verify.sql
```

Capture the one generated `fyp_user` password directly into the deployment secret store.
`02-schema.sql` is a non-idempotent empty-database installer: it creates 17 tables, grants
CRUD on fourteen ordinary state tables, grants only `SELECT`/`INSERT` on `audit_logs`, and
limits `audit_chain_heads` updates to `last_log_id`, `current_hash`, and `updated_at` so the
runtime account cannot alter `schema_revision`. It has no access to `alembic_version`.
`03-verify.sql` is read-only and must also show that the retired
`fyp_migrator` identity is absent. Only after every result passes review should the
application start as `fyp_user` through the standard `DB_*` settings.

Do not rerun the empty-schema installer on a non-empty database. Future upgrades require a
separate, versioned, reviewed DBA SQL script and a verified backup. See
[DEPLOYMENT.md](docs/DEPLOYMENT.md) for remote account-host customization, exact grants,
failure recovery, and release safeguards.

The staging VPS automatically deploys an exact commit after a reviewed pull request is merged
into `main`. See [AUTOMATIC_DEPLOYMENT.md](docs/AUTOMATIC_DEPLOYMENT.md) for the server-pull
workflow, operator commands, failure quarantine, and credential boundary.

OpenAPI: <http://localhost:8000/docs> locally, or
<https://secureview.tech/docs> on the public staging deployment.

Run backend quality checks from `backend/`:

```bash
ruff format --check app tests migrations
ruff check app tests migrations
pytest
alembic check
pip-audit -r requirements.txt
```

`alembic check` remains a development/CI drift check; it is not a production deployment
step.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: <http://localhost:5173>

## Important Security Note

This remains an FYP prototype. Email verification and forgotten **login-password** reset are
implemented through one-time codes, but MFA and external identity providers are not.
The encryption passphrase is separate and never reaches the server: forgetting it still
requires the user's separately retained private-key file, and recovery does not reset the
stored passphrase. The built-in password deny-list is deliberately small and is not a
maintained breached-password corpus. A production deployment additionally needs encrypted
off-server backup/restore drills, stronger recovery-key custody through a KMS/HSM or equivalent
offline controls, externally anchored audit checkpoints, and independent professional
security review.
