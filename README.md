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

- Client-side file encryption with six AEAD suites: AES-GCM (128/192/256-bit keys), AES-256-GCM-SIV, ChaCha20-Poly1305 and XChaCha20-Poly1305
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
[SECURITY_FLOWS.md](docs/SECURITY_FLOWS.md); what those flows do and do not defend against, and
the open findings, are in the self-assessed [THREAT_MODEL.md](docs/THREAT_MODEL.md).

The browser MVP is operational end to end: emailed-code registration and password reset,
client-held account-key enrolment, passphrase or private-key-file unlock, passphrase reset
with the private-key file, idle relock,
authenticated encryption before upload, local decryption after download, filename search,
sharing by rewrapping the file key to the recipient, revocation, per-file access history,
silent session refresh, logout, and account deletion. AES-128/192/256-GCM,
AES-256-GCM-SIV, ChaCha20-Poly1305 and XChaCha20-Poly1305 are selectable per file; AES-256-GCM
remains the default. The former
hard-coded credential and demo-token fallbacks are gone.

Public product pages sit beside the authenticated workspace: `/` is the marketing landing
("Encryption and Sharing" hero plus scrolling Core Features), `/education` teaches algorithms
with demos and a knowledge base, `/help` points to the homepage picture guide and keeps video
placeholders for longer clips, and `/team` (**Contact us**) shows a feedback form preview plus
the development roster. `/benchmark/argon2`, linked from no menu, times the unlock key derivation
on the visiting device; it is the evidence behind the threat model's passphrase analysis.
The language switch sits in the header bar itself, never inside a menu. Signed-in users get a
header avatar menu with theme controls, `/profile` and `/settings`; signed-out visitors open the
theme controls from the settings icon to the right of the language switch.
The active nav label uses the theme primary colour so the current tab is obvious. `/profile` can
upload or remove a validated PNG/JPEG picture (initials remain the fallback).

Every page has a **Help assistant** button at the bottom right (#146). It answers how-to,
how-it-works and "why not Google Drive / WhatsApp / email" questions with a short summary, steps
and links into the product, matching the question in the browser against curated answers and the
Education, explainer and picture-guide content. There is no language model and no network call;
questions are not sent or logged. Signed in, it also answers questions about your own account
(#148): who has access to a file, what has been shared with you, recent failed sign-ins. Those
answers only read what My Files and Access Records already show, and change nothing. See
[docs/HELP_ASSISTANT.md](docs/HELP_ASSISTANT.md).

The interface can be switched between **English and 简体中文** (#74) from the header bar,
the phone menu or Settings; the choice is remembered on
the device. File names, usernames and anything a user wrote are never translated. The Chinese is
drafted at build time by Zhipu `glm-4-flash` and checked against a fixed security glossary; the
browser never calls a translation service. See [docs/I18N.md](docs/I18N.md).

Core Features uses a dual-row `FeatureLane` with autoplay plus touch, mouse-drag and keyboard
scrolling (no native scrollbar), and a static complete-card layout for reduced-motion
preferences. The file lifecycle explainer sits below Upload; Upload, Education, Help, Access
Records and My Files share Contact us page styling. See
[changelog/CHANGELOG.md](changelog/CHANGELOG.md#ui-layout-and-navigation-consistency-junyan9--界面排版与导航一致性junyan9).

The homepage's How it works section offers six annotated screenshots from the real UI under
`/#how-it-works`, covering file selection, encryption, sharing, unlock, and recipient download.
Visitors can pause, enlarge images, swipe on phones, or let 8-second autoplay run with a visible
progress bar. Completed steps show a check. The pictures use fabricated data and
mobile crops; this local preview is not yet verified on staging.

The remaining work is production hardening rather than an unfinished basic demo: change-passphrase
(with the old one) and successor-key UI, complete admin/recovery-officer screens, observability,
and formal security review. Required CI, MySQL 8.4 release gates, encrypted off-server backups,
clean-host restore evidence, scheduled reconciliation, and a same-VPS isolated tamper drill are
now in place. The prioritized summary is in [TODO.md](TODO.md), and executable
work with acceptance criteria is tracked in [GitHub Issues](https://github.com/jsonrar/fyp-secure-file-platform/issues)
and the team's [SecureView Development Board](https://github.com/users/Waldo0926/projects/1).

The file manager also offers **Download encrypted** for owners and authorized recipients,
including while the vault is locked. It saves the verified stored bytes as
`<filename>.ciphertext` without a passphrase or private key. **Encrypted preview**, under each
file, shows what the server really stores: the exact sizes, the recorded SHA-256 and a hex dump
of the first 128 bytes of ciphertext, for owned and received files alike. Why the two sizes match,
and how to show it live, is in [docs/ENCRYPTION_EVIDENCE.md](docs/ENCRYPTION_EVIDENCE.md).

While a file uploads, the Upload page shows the real steps for it (read in the browser, encrypt
and self-check, wrap the file key with RSA-OAEP, upload the ciphertext with a real progress bar),
each with its measured time, and then the file's first 16 bytes beside the first 16 bytes the
server receives. Encryption takes tens of milliseconds, so without this an upload looked as if
nothing had been encrypted; nothing is slowed down to look busy.

**Measured capacity (staging, 2026-10-03/04, #140):** 22,264 operations, 5,094 downloads
SHA-256-verified with 0 integrity failures, every common file type up to 500 MiB byte-exact; no
server error up to 50 concurrent users; at 100 the API's 15-connection database pool is the first
limit while CPU averages 3 %. Read the test conditions before quoting a number:
[docs/performance/REPORT-2026-10-03.md](docs/performance/REPORT-2026-10-03.md) and the conclusions
in [docs/PERFORMANCE_TESTING.md](docs/PERFORMANCE_TESTING.md).

**Upload limits (threat model F-09):** each account may store 2 GiB and upload 5 GiB per 24 hours,
uploads stop while the storage disk is below a free-space floor, nginx allows ten uploads in flight
per address, and the security agent reports upload bursts. Because the server only ever holds
ciphertext it cannot scan for malware, so a recipient is warned before saving a shared program or
macro-capable file. See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) §11.3.

What to say in the final presentation, with the evidence for each point, is in
[docs/presentation/TALKING_POINTS.md](docs/presentation/TALKING_POINTS.md); what is still missing
and what to do about it, by priority, is in
[docs/presentation/REFLECTION.md](docs/presentation/REFLECTION.md). The live tamper demonstration
(change the stored ciphertext on staging, and the recipient's download is refused) is scripted in
[docs/presentation/TAMPER_DEMO.md](docs/presentation/TAMPER_DEMO.md).

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
4. **Manage files:** `/files` searches and pages through "My Files" and "Shared with me". Owners can create, rename, and delete folders, move files between them, and take files out of a folder; deleting a folder never deletes its encrypted files.
   Download first verifies the server-side ciphertext SHA-256, then the browser unwraps the
   DEK, authenticates the AEAD tag, and saves the plaintext. A failed authentication never
   saves a partial file. **Download encrypted** instead saves the ciphertext without
   unlocking; sign-in and download permission are still required. The `.ciphertext` file
   contains only the stored bytes, not the separately stored envelope, nonce, tag, or wrapped
   key, so it is not a standalone offline-decryption backup. Deleting an owned file asks for
   confirmation and states that shares are revoked and the action cannot be undone.
5. **Share and revoke:** The owner unlocks first if needed, then enters an existing user's
   exact username or email address. The browser
   rewraps the same DEK to the recipient's public key, and the recipient opens it with their
   own passphrase; the server never learns the DEK. Revocation confirms first, then stops
   future server-mediated access; it cannot recover a copy the recipient already downloaded
   and decrypted.
6. **Audit and account actions:** `/audit-logs` shows sign-in, upload, download, share, and
   revocation events. Owners can inspect activity on their files, recipients see only events
   involving themselves, and ADMIN can verify the full hash chain. An emailed code resets a
   forgotten login password; a forgotten encryption passphrase requires the separately
   retained `.pem` key, which can unlock the current session or, in `/settings`, set a new
   passphrase without changing the account key or any file. Account identity and preferences live
   under the header avatar: `/profile` shows the signed-in account, can upload or remove a
   profile picture, and can open account deletion; `/settings` covers theme and the same
   deletion flow (password + typed `DELETE`).
7. **Learn and get help without signing in:** `/education` covers Algorithm Explorer,
   Playground, and Knowledge Base. The homepage `#how-it-works` slideshow is the fastest first
   share guide; `/help` links to it and keeps video placeholders. `/team` is labelled
   **Contact us**: a demo feedback form sits above the team roster. The header highlights the
   active tab in the theme colour.

### Roles and administration

- `USER` uses upload, download, sharing, revocation, and personal audit features.
- `ADMIN` can manage users/files, verify the audit chain, register recovery public keys, and
  review recovery requests through `/admin`.
- `RECOVERY_OFFICER` can review recovery requests on `/admin` but cannot approve a request they
  created.
- Any signed-in user can open a recovery request from My Files and track or cancel it on
  `/admin`. Executing an approved request still requires an offline rewrap with the recovery
  private key; that private key is never accepted by the browser UI.

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
| File Encryption | AES-128/192/256-GCM, AES-256-GCM-SIV, ChaCha20-Poly1305, XChaCha20-Poly1305 (default: AES-256-GCM) |
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
`0007_file_folders`. Local development exposes `/docs`, `/redoc`, and `/openapi.json`;
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
|   |-- THREAT_MODEL.md
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

[`changelog/CHANGELOG.md`](changelog/CHANGELOG.md) is the team's single active change record. It
records **what changed in the product and why it mattered**, including endpoints, security fixes,
contract changes, testing evidence, and deployment behaviour. Current entries are under
`[Unreleased] / [未发布]`, normally newest first.

[`changelog/work-packages/`](changelog/work-packages/) is retained only as a read-only historical
archive of the early cryptography and testing packages. Do not start or extend personal or
track-specific logs there; new work from every contributor belongs in the shared changelog, with
README and TODO updated whenever current capabilities or remaining work change.

The existing changelog's main work streams are:

1. **Client cryptography:** account-key enrolment, AES-GCM(-SIV)/(X)ChaCha20-Poly1305 file envelopes,
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
- [SecureView Development Board](https://github.com/users/Waldo0926/projects/1): five team views
  for active backlog, proposal WBS, milestones, acceptance criteria, and PR evidence through
  Backlog, Ready, In progress, In review, and Done. Historical direct-to-`main` CT work is retained
  in the traceability document and archive rather than a separate personal board view or a
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
`0007_file_folders` schema revision.

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
`02-schema.sql` is a non-idempotent empty-database installer: it creates 18 tables, grants
CRUD on fifteen ordinary state tables, grants only `SELECT`/`INSERT` on `audit_logs`, and
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

## Continuous Integration

`.github/workflows/ci.yml` runs on every pull request and on push to `main`, with five jobs.
`backend` and `frontend` are required checks by convention: GitHub branch protection is not
available while the repository is private on the free plan, so nothing stops a merge on red CI
except the reviewer. Run the same commands locally before pushing so a failure never arrives
as a surprise in CI:

```bash
# backend (from backend/, matches the "backend" job; fails below 78% branch coverage)
uv venv --python /opt/homebrew/bin/python3.12 .venv   # or any Python 3.12 interpreter
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
uv pip install --python .venv/bin/python pip-audit && .venv/bin/pip-audit -r requirements.txt
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -m pytest -m "not integration" --cov

# frontend (from frontend/, matches the "frontend" job; thresholds in vite.config.ts)
npm ci
npm audit --audit-level=high
npm run test:coverage
npm run typecheck
npm run build
```

A third job, `mysql-gate`, provisions a disposable MySQL 8.4 service with verified TLS, runs
every migration from empty through `0007_file_folders`, then `alembic current` and
`alembic check`, then the whole backend suite against it — unit tests plus every MySQL
integration test, including the multi-connection concurrency and fault-injection suites —
failing the job if any test is skipped or branch coverage falls below 82%, followed by grant-
boundary, schema-parity, non-empty-database-refusal, idempotent-resume, concurrent-migration-
lock, and backup/restore checks. `backend/scripts/mysql_release_gate.sh` exercises the harder
scenarios locally during development of the gate itself.

The fourth job, `e2e-live`, starts the real API against another disposable MySQL and runs every
frontend live-backend suite un-skipped: registration with an emailed code, login/refresh/
replay/logout, unlock, all four file algorithms, sharing and revocation, audit visibility, role
denial, and account deletion. It then runs a Chromium smoke test (Playwright) that clicks the
built pages through the same golden path, so a button wired to the wrong handler fails CI. Each
job publishes its JUnit and coverage reports as a build
artifact, but only after `backend/scripts/check_report_hygiene.py` confirms they hold no keys,
tokens, non-example addresses, or fixture plaintext.

The fifth job, `tamper-drill`, builds a default-stopped attacker container on an internal-only
Docker network. Against its own MySQL 8.4 `_test` database and encrypted-object volumes, it
proves that byte modification is shown as `MODIFIED`/`CORRUPTED`, download is refused, a missing
object is reported without permanently corrupting status, and a restored object returns to
`VALID`/`ACTIVE`. It also documents the trust boundary: an attacker controlling both the object
store and database can replace the recorded SHA-256, but the browser's AEAD tag still rejects
the forged ciphertext. See [`security-lab/README.md`](security-lab/README.md).

Both database suites run from a laptop against any disposable MySQL 8.4 whose database name has
a `_test` segment (never the shared `docker compose` database):

```bash
docker run -d --name my-test-mysql -e MYSQL_ROOT_PASSWORD=... -p 127.0.0.1:3310:3306 mysql:8.4
# create a utf8mb4_unicode_ci database such as fyp_local_test, then:

# MySQL integration, concurrency and fault injection (from backend/, schema migrated first)
AUTH_TEST_DATABASE_URL='mysql+pymysql://USER:PASS@127.0.0.1:3310/fyp_local_test' \
  SECRET_KEY=local-test-secret-key-at-least-32-chars APP_ENV=test \
  .venv/bin/python -m pytest -m integration -rs

# The live end-to-end stack (from the repository root; migrates, seeds, serves, and cleans up)
DB_HOST=127.0.0.1 DB_PORT=3310 DB_USER=USER DB_PASSWORD=PASS DB_NAME=fyp_local_test \
  bash backend/tests/e2e/run_live_stack.sh
# add E2E_BROWSER=1 for the Chromium smoke test too (once: cd frontend && npx playwright install chromium)
```

See [`docs/E2E_TESTING.md`](docs/E2E_TESTING.md) for what each suite proves, `backend/scripts/`
for the individual check scripts, and `TODO.md` for what remains deferred.

### Security agent

Admin → **Security agent** ranks what needs an administrator's attention from the audit log, integrity
checks and recovery requests, as Critical / High / Medium / Low findings with the evidence and a
recommended action. It is rule-based, read-only and sees metadata only; see
[docs/SECURITY_AGENT.md](docs/SECURITY_AGENT.md) for its inputs, rules, output and boundaries.

### Backups and the restore drill

Encrypted, coordinated backups of MySQL metadata and ciphertext objects, and the clean-host
restore that proves them, are described in
[docs/BACKUP_AND_RECOVERY.md](docs/BACKUP_AND_RECOVERY.md) (RPO/RTO, retention, key custody,
measured timings). `mysql-gate` runs the drill on every pull request. To run it locally against
any disposable MySQL 8.4 (it only touches databases whose names contain `_test`, and generates
throwaway keys and accounts that are deleted on exit):

```bash
docker compose up -d mysql
cd backend
export DB_HOST=127.0.0.1 DB_PORT=3306 ADMIN_DB_USER=root ADMIN_DB_PASSWORD=local_root_password
export SECRET_KEY=local-test-secret-key-at-least-32-chars APP_ENV=test
bash scripts/backup_restore_drill.sh   # encrypted backup -> clean restore -> refusal checks
bash scripts/mysql_release_gate.sh     # lock races, checksummed restore, rollback, partial DDL
```

The nightly backup job itself (`deployment/server/mcs21-offsite-backup.{service,timer}` with the
`database/mysql/04-backup-account.sql` account) is a template and is not yet installed on
staging.

### Reconciliation and ops alerts

SecureView's #59 observability hardening is implemented in the repository: structured redacted
security/operations events feed a loopback-only metrics snapshot and five-minute threshold
watcher; hourly HMAC-authenticated audit-chain checkpoints are designed for the existing
S3-compatible off-server store; alert email carries unit state but no raw journal lines. The
trusted-proxy boundary is loopback nginx only and the public origin explicitly returns 404 for
`/internal/`. Installation, threshold ownership, independent checkpoint verification, and
incident procedures are in
[`docs/OBSERVABILITY_AND_INCIDENT_RESPONSE.md`](docs/OBSERVABILITY_AND_INCIDENT_RESPONSE.md).
The new timers remain deliberately opt-in until the exact merged SHA is deployed and the
staging evidence table is completed.

`backend/scripts/reconcile.py` removes lapsed sessions, refresh tokens, throttle buckets,
verification codes, and unreferenced ciphertext objects; it never touches audit, identity,
key-custody, or recovery tables. It reports by default, shows each category on both sides of
its cutoff, and with `--apply` refuses to delete anything (exit 3) when the volume is unusual.
`deployment/server/mcs21-reconcile.{service,timer}` run it daily at 05:00 Asia/Kuala_Lumpur,
after the same-host backup, and `mcs21-alert@.service` emails a person when it or any backup
job fails. None of this is enabled on staging until the report-only review in
[docs/RECONCILIATION_RUNBOOK.md](docs/RECONCILIATION_RUNBOOK.md) is recorded
([#57](https://github.com/jsonrar/fyp-secure-file-platform/issues/57)).

## Important Security Note

This remains an FYP prototype. Email verification and forgotten **login-password** reset are
implemented through one-time codes, but MFA and external identity providers are not.
The encryption passphrase is separate and never reaches the server: forgetting it still
requires the user's separately retained private-key file, which can reset it for accounts
holding a single key; the admin recovery workflow cannot reset it. The built-in password deny-list is deliberately small and is not a
maintained breached-password corpus. A production deployment additionally needs encrypted
off-server backup/restore drills, stronger recovery-key custody through a KMS/HSM or equivalent
offline controls, externally anchored audit checkpoints, and independent professional
security review.
