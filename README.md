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

Public product pages sit beside the authenticated workspace: `/` is the marketing landing
("Encryption and Sharing" hero plus scrolling Core Features), `/education` teaches algorithms
with demos and a knowledge base, `/help` points to the homepage picture guide and keeps video
placeholders for longer clips, and `/team` (**Contact us**) shows a feedback form preview plus
the development roster.
Signed-in users get a header avatar menu with theme control, `/profile`, and `/settings`; the
active nav label uses the theme primary colour so the current tab is obvious.

Core Features now uses a seamless dual-row loop, with hover-to-pause and a static,
complete card layout for reduced-motion preferences. This is a local frontend update;
deployment has not yet been verified. See the
[landing polish changelog](changelog/CHANGELOG.md#landing-hero-and-feature-marquee-polish--首页主标题与功能滚动条打磨).

The homepage's How it works section offers six annotated screenshots from the real UI under
`/#how-it-works`, covering file selection, encryption, sharing, unlock, and recipient download.
Visitors can pause, enlarge images, swipe on phones, or let 8-second autoplay run with a visible
progress bar. Completed steps show a check. The pictures use fabricated data and
mobile crops; this local preview is not yet verified on staging.

The remaining work is production hardening rather than an unfinished basic demo: required CI
and MySQL 8.4 gates, passphrase-change and successor-key UI, complete admin/recovery-officer
screens, encrypted off-server backup/restore drills, scheduled reconciliation, observability,
and formal security review. The prioritized summary is in [TODO.md](TODO.md), and executable
work with acceptance criteria is tracked in [GitHub Issues](https://github.com/jsonrar/fyp-secure-file-platform/issues)
and the team's [SecureView Development Board](https://github.com/users/Waldo0926/projects/1).

## Using the Website

### Standard user flow

1. **Register:** At `/register`, provide a username, email, login password, and a separate
   encryption passphrase, then complete email-code verification. The browser generates the
   RSA key pair, AMK, and sealed private-key bundle locally. Move the one-time `.pem` private
   key out of Downloads and store it safely. The login password authenticates the account;
   the encryption passphrase unlocks files, and neither replaces the other.
2. **Sign in and open the workspace:** `/login` leads to `/dashboard`. When an access token
   expires, the frontend rotates the one-time refresh token and retries the interrupted
   request. It clears the session and returns to sign-in only when renewal cannot succeed.
3. **Encrypt and upload:** At `/upload`, choose a file and algorithm. The browser generates a
   per-file DEK, performs authenticated encryption locally, and wraps the DEK to the account
   RSA public key. The server receives ciphertext, public metadata, and wrapped keys—not the
   plaintext file or plaintext DEK.
4. **Manage files:** `/files` searches and pages through "My Files" and "Shared with me".
   Download first verifies the server-side ciphertext SHA-256, then the browser unwraps the
   DEK, authenticates the AEAD tag, and saves the plaintext. A failed authentication never
   saves a partial file.
5. **Share and revoke:** The owner enters an existing user's exact username. The browser
   rewraps the same DEK to the recipient's public key, and the recipient opens it with their
   own passphrase; the server never learns the DEK. Revocation stops future server-mediated
   access but cannot recover a copy the recipient already downloaded and decrypted.
6. **Audit and account actions:** `/audit-logs` shows sign-in, upload, download, share, and
   revocation events. Owners can inspect activity on their files, recipients see only events
   involving themselves, and ADMIN can verify the full hash chain. An emailed code resets a
   forgotten login password; a forgotten encryption passphrase requires the separately
   retained `.pem` key to unlock the current session. Account identity and preferences live
   under the header avatar: `/profile` shows the signed-in account, and `/settings` covers
   theme and account actions including deletion.
7. **Learn and get help without signing in:** `/education` covers Algorithm Explorer,
   Playground, and Knowledge Base. The homepage `#how-it-works` slideshow is the fastest first
   share guide; `/help` links to it and keeps video placeholders. `/team` is labelled
   **Contact us**: a demo feedback form sits above the team roster. The header highlights the
   active tab in the theme colour.

### Roles and administration

- `USER` uses upload, download, sharing, revocation, and personal audit features.
- `ADMIN` can use backend APIs to manage users/files, verify the audit chain, register recovery
  public keys, and review recovery requests.
- `RECOVERY_OFFICER` can review recovery requests but cannot approve a request they created.
- `/admin` currently provides a limited recovery-request overview. The complete admin and
  recovery-officer UI remains in the backlog, so some operations currently require an
  authorized API/OpenAPI client.

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

## FastAPI Backend Overview

FastAPI is this project's HTTP/API framework; it does not decrypt users' files. It validates
requests, authenticates and authorizes actors, dispatches use cases, manages database
transactions, accesses encrypted object storage, and generates the OpenAPI contract. The
entry point is `backend/app/main.py`. Its application factory wires settings, the SQLAlchemy
engine/session factory, password manager, middleware, exception handlers, and `/api/v1`
routers, then disposes the connection pool during shutdown.

A typical request follows this path:

```text
Browser Axios request
  -> FastAPI middleware (body limits, CORS)
  -> Router (path, Pydantic request/response, Depends)
  -> Identity/RBAC dependency (Bearer token -> ActorContext)
  -> Service (use case, transaction, audit, storage compensation)
  -> Repository / SQLAlchemy Session + encrypted object storage
  -> Consistent JSON response
```

Layer responsibilities:

- `api/v1/routers/` defines Auth, Keys, Files, Sharing, Audit, Recovery, and Admin endpoints.
  Routers handle HTTP input/output and contain no direct SQL or filesystem operations.
- `api/dependencies.py` creates a request-scoped database session, resolves bearer tokens,
  applies ADMIN/recovery-reviewer checks, and constructs services.
- `schemas/` uses Pydantic for strict transport DTO validation and drives OpenAPI/Swagger.
- `services/` owns each use-case transaction and coordinates repositories, ciphertext
  storage, domain policy, and audit appends.
- `repositories/` and `models/` isolate persistence operations and SQLAlchemy models.
  Repositories may query, add, and `flush`, but never own `commit`.
- `core/` centralizes environment settings, database composition, and security primitives
  such as Argon2id and bearer-session handling.

Business APIs are mounted under `/api/v1`. Verification, registration, login, password reset,
and refresh are the main public endpoints. Other endpoints require a bearer token through
`Depends`, with role or resource authorization added for sensitive actions. Successful
responses use the `success/status/message/data/code` envelope, while centralized handlers
map domain failures to stable HTTP responses. `/health/live` checks the process;
`/health/ready` also queries MySQL and requires the stored schema revision to equal
`0006_chacha20_poly1305`. Local development exposes `/docs`, `/redoc`, and `/openapi.json`;
a deployment can unmount all three with `APP_DOCS_ENABLED`.

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
|   |-- E2E_TESTING.md
|   |-- SECURITY_FLOWS.md
|   |-- PROJECT_SCOPE.md
|   `-- crypto/
|       |-- FILE_ENVELOPE.md
|       `-- test_vectors.json
|-- recovery_keys/
|-- TODO.md
|-- TODO.zh-CN.md
|-- .env.example
|-- .gitignore
`-- docker-compose.yml
```

## Change Log: What It Records and How to Maintain It

The changelog uses two complementary records:

- [`changelog/CHANGELOG.md`](changelog/CHANGELOG.md) records **what changed in the product and
  why it mattered**, such as a new endpoint, security fix, contract change, or deployment
  behavior. Current entries are under `[Unreleased] / [未发布]`, normally newest first.
- [`changelog/work-packages/`](changelog/work-packages/) records **how a piece of work was
  carried out**, including its starting commit, scope, verification, and deliberately retained
  limitations. Work that both progresses a package and changes the product belongs in both;
  they are not duplicate records.

The existing changelog's main work streams are:

1. **Client cryptography:** account-key enrolment, AES-GCM/ChaCha20-Poly1305 file envelopes,
   browser decryption, `.pem` unlock, sharing DEK rewrap, and cross-language vectors.
2. **Authentication and account security:** emailed codes, password reset, Argon2id policy,
   refresh rotation, session invalidation, and account deletion.
3. **Files and sharing UX:** paging/search, owner/recipient separation, integrity states,
   notifications, revocation, and per-file history.
4. **Audit and privacy:** hash chaining, audit contracts and labels, filename resolution, and
   the visibility rule that users see their own activity plus activity on files they own.
5. **Database and operations:** least-privilege MySQL SQL, schema revisions, reconciliation,
   HTTPS, nginx/fail2ban, guarded deployment, failed-SHA quarantine, and release safeguards.
6. **UI and development environment:** signed-in navigation and account menu, theme/branding,
   Education / Help / Team public pages, the landing hero and feature marquee, dependency
   pinning, type checking, and test baselines.

Before adding an entry, read [`changelog/README.md`](changelog/README.md). Add paired English
and Simplified Chinese lines under the relevant topic and explain why the change mattered
rather than repeating the diff. Historical entries describe the state at that time; when a
newer entry closes an old limitation, prefer the newer entry, the current README, and code.

## Team Workflow and Sources of Truth

- `changelog/CHANGELOG.md`: what shipped and why it mattered.
- GitHub Issues: executable remaining work, ownership, discussion, and acceptance criteria.
- [SecureView Development Board](https://github.com/users/Waldo0926/projects/1): separate views
  for active backlog, the proposal WBS, milestones, acceptance criteria, PR evidence, and direct
  CT work packages through Backlog, Ready, In progress, In review, and Done. Historical
  direct-to-main work uses explicit Contributor and Commit evidence fields rather than a
  fabricated retroactive PR.
- [`docs/PROPOSAL_TRACEABILITY.md`](docs/PROPOSAL_TRACEABILITY.md): the dated evidence map from
  proposal commitments to repository and deployment results.
- `TODO.md`: prioritized summary linked to those Issues, not a second independent backlog.
- `README.md`: current user-facing capabilities, setup, and deployment entry points.

Every pull request must review all four, update the affected records, and explain any
intentional `N/A`. Runtime changes are not complete at merge: after `main` deploys, record the
deployed SHA and verify health plus the changed user-visible path. The repository pull-request
template carries this checklist.

## Local Setup

All backend business routers are operational. Health, readiness, and OpenAPI are available;
protected routes require bearer authentication and the admin/recovery routes enforce RBAC.
Readiness checks both database connectivity and the exact
`0006_chacha20_poly1305` schema revision.

`MAX_REQUEST_BODY_BYTES` limits ordinary JSON/form bodies (1 MiB by default, configurable up
to 8 MiB). Encrypted multipart upload has a separate
`MAX_UPLOAD_SIZE_BYTES + MAX_UPLOAD_REQUEST_OVERHEAD_BYTES` cap, so increasing the ordinary
body limit does not increase the permitted ciphertext size.

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
