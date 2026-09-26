# Frontend

[English](README.md) | [简体中文](README.zh-CN.md)

Vue 3 + TypeScript frontend integrated with SecurFile UI and FYP backend APIs.

## Run

```bash
npm install
npm run dev
```

Backend should be running at `http://localhost:8000`.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing (hero + features) |
| `/login` | Sign in |
| `/register` | Register + private key display |
| `/forgot-password` | Email-code login-password reset |
| `/dashboard` | Signed-in workspace |
| `/upload` | File encryption upload (auth required) |
| `/files` | File management (auth required) |
| `/audit-logs` | Audit access records (auth required) |
| `/admin` | Role-aware operations: recovery review, admin users/files, audit chain, recovery key |
| `/education` | Education page |
| `/help` | Product help — links to homepage picture guide; video placeholders |
| `/team` | Contact us — feedback form preview + development team |

## Structure

- `src/components/securfile/` — UI migrated from SecurFile
- `src/api/` — Axios clients aligned with backend `/api/v1`
- `src/crypto/` — authenticated file encryption/decryption and sharing-key rewrap
- `src/stores/` — Pinia auth/file state
- `src/composables/useTheme.ts` — System/light/dark theme

The browser implements account-key enrolment, passphrase/private-key-file unlock, encrypted
upload, authenticated download/decryption, sharing-key rewrap, revocation, search, audit
history, refresh rotation, server-revoking logout, account deletion, and role-aware
admin/recovery/audit operations on `/admin`. Passphrase change and successor-key rotation
remain backlog work.

On `/files`, **Download encrypted** saves the stored ciphertext as `<filename>.ciphertext`
without unlocking the account key; **Download and decrypt** still opens the unlock dialog
when needed and saves the original file. Both use the authenticated, integrity-checked
`POST /files/{file_id}/download` endpoint. Encrypted downloads contain only the stored blob,
not a complete offline-decryption envelope.

## Environment

The default API base is already `http://localhost:8000/api/v1`. To override it, create an
untracked `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
