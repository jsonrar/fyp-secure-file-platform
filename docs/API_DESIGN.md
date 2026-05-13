# API Design

Base path:

```text
/api/v1
```

## Auth API

| Method | Endpoint | Description |
|---|---|---|
| POST | /auth/register | Register a new user and generate key pair |
| POST | /auth/login | Login and receive token/session |
| POST | /auth/logout | Logout current session |
| GET | /auth/me | Get current user info |

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
