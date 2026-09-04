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
| `/admin` | Limited admin/recovery overview (auth required) |
| `/education` | Education page |
| `/team` | Development team page |

## Structure

- `src/components/securfile/` — UI migrated from SecurFile
- `src/api/` — Axios clients aligned with backend `/api/v1`
- `src/crypto/` — authenticated file encryption/decryption and sharing-key rewrap
- `src/stores/` — Pinia auth/file state
- `src/composables/useTheme.ts` — System/light/dark theme

The browser implements account-key enrolment, passphrase/private-key-file unlock, encrypted
upload, authenticated download/decryption, sharing-key rewrap, revocation, search, audit
history, refresh rotation, logout, and account deletion. Passphrase change, successor-key
rotation, and the complete role-aware admin/recovery UI remain backlog work.

## Environment

The default API base is already `http://localhost:8000/api/v1`. To override it, create an
untracked `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
