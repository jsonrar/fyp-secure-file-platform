# API Design

English | [简体中文](API_DESIGN.zh-CN.md)

## Current Status

Auth is the first implemented business router. Its nine endpoints use real persistence,
transactions, server-side sessions, throttling, audit events, and API/service tests.

File, sharing, audit-query, recovery, and admin routes remain contract placeholders. They
are visible in OpenAPI but guarded with `501 feature_not_implemented` until each router has
real authorization, persistence, transaction ownership, audit behavior, storage handling
where applicable, and tests. They must not return demo tokens, hard-coded users, or
synthetic success responses.

Base path:

```text
/api/v1
```

Unversioned operational endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | /health/live | Process liveness; does not check dependencies |

## Response and Error Contract

Application responses use one envelope while the public DTO inside `data` remains typed:

```json
{
  "success": false,
  "status": "fail",
  "message": "Request validation failed",
  "data": {
    "error_code": "request_validation_failed",
    "details": []
  },
  "description": null,
  "code": 422
}
```

`error_code` is stable for clients; `message` is safe for users. Internal exception text,
request bodies, credentials, keys, database details, and filesystem paths are never returned.
Validation errors identify field locations without echoing rejected input.

Protected routes accept the opaque session token using `Authorization: Bearer <token>`.
Authentication failures include `WWW-Authenticate: Bearer`. Every Auth response, including
validation and domain errors, includes `Cache-Control: no-store, no-cache` and
`Pragma: no-cache`; access tokens, refresh tokens, and the registration private key must not
be cached or logged.

## Auth API

| Method | Endpoint | Auth | Success | Description |
|---|---|---|---:|---|
| POST | `/auth/register` | Public | 201 | Create a USER account and return its RSA private key once |
| POST | `/auth/login` | Public | 200 | Verify `username`/`password` and issue an access/refresh pair |
| POST | `/auth/refresh` | Refresh token in JSON body | 200 | Consume and rotate the one-time refresh credential |
| GET | `/auth/me` | Bearer | 200 | Return the current account using its public UUID |
| POST | `/auth/logout` | Bearer | 200 | Revoke the current session family |
| POST | `/auth/logout-all` | Bearer | 200 | Revoke every active session family for the account |
| POST | `/auth/change-password` | Bearer | 200 | Verify current password, change it, and revoke every session |
| GET | `/auth/sessions` | Bearer | 200 | List up to the 100 newest server-side sessions |
| DELETE | `/auth/sessions/{session_id}` | Bearer | 200 | Revoke one account-owned session by public UUID |

Login keeps the JSON request contract `{ "username": "...", "password": "..." }`.
Its successful `data` object is flat and contains `user`, `access_token`, `refresh_token`,
`token_type`, `access_expires_at`, `refresh_expires_at`, and `session_id`. Sequential user
and session database IDs never cross the API boundary.

Access and refresh credentials are independent opaque random values. The server stores only
their SHA-256 hashes. A refresh credential is valid for one rotation; replaying a consumed
credential revokes its complete session family. Access expiry is short-lived, refresh expiry
is longer, and both remain bounded by the session's absolute expiry.

Registration and new-password inputs are Unicode NFC-normalized. New passwords must contain
15 to 128 characters and pass the local common/account-derived password checks before Argon2id
hashing. The local list is not a complete or maintained breached-password service.

Stable Auth errors include `invalid_credentials`, `authentication_required`,
`invalid_refresh_token`, `account_identifier_unavailable`, `password_unchanged`,
`weak_password`, `invalid_current_password`, `session_not_found`, and
`auth_rate_limited`. The 429 response supplies `Retry-After`; authentication errors never
distinguish unknown, disabled, expired, or revoked principals.

Forgotten-password reset, email verification, MFA, and external identity-provider login are
not implemented. Each requires a trusted out-of-band delivery, enrollment, or federation
channel. The presence of `email_verified` in account metadata is not a claim that a
verification flow exists.

## Unimplemented Business APIs

Every endpoint in the following sections currently returns
`501 feature_not_implemented`.

## File API

| Method | Endpoint | Description |
|---|---|---|
| POST | /files/upload | Upload and encrypt a file |
| GET | /files | List files accessible by the current user |
| GET | /files/{file_id} | Get file metadata |
| POST | /files/{file_id}/download | Download and decrypt file after permission check |
| DELETE | /files/{file_id} | Delete or disable a file |
| POST | /files/{file_id}/integrity-check | Verify encrypted file hash |

## Sharing API

| Method | Endpoint | Description |
|---|---|---|
| POST | /files/{file_id}/share | Share file with another user |
| GET | /files/{file_id}/shared-users | List users who can access file |
| POST | /files/{file_id}/revoke | Revoke a user's access |

## Audit API

| Method | Endpoint | Description |
|---|---|---|
| GET | /audit-logs | List audit logs |
| GET | /audit-logs/file/{file_id} | List logs for a file |
| POST | /audit-logs/verify-chain | Verify audit hash chain |

## Recovery API

| Method | Endpoint | Description |
|---|---|---|
| POST | /recovery/request | Create recovery request |
| POST | /recovery/{request_id}/approve | Approve recovery request |
| POST | /recovery/{request_id}/execute | Execute recovery action |
| GET | /recovery/requests | List recovery requests |

## Admin API

| Method | Endpoint | Description |
|---|---|---|
| GET | /admin/users | List users (admin only) |
| GET | /admin/files | List file records (admin only) |

## Contract Rules

- Routers declare request and response models; ORM objects and infrastructure dictionaries
  never become responses directly.
- Public resources use opaque identifiers. Sequential database IDs are internal.
- Collection endpoints define stable ordering plus either pagination or an explicit hard
  result bound before implementation. Auth session history uses a 100-row hard bound.
- Commands that may be retried (upload finalisation, share, revoke, recovery execution) need
  an idempotency or conditional-state strategy.
- Authentication failures do not reveal whether an account, file, session, or key exists.
