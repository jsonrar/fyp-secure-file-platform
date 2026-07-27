# Frontend

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
| `/upload` | File encryption upload (auth required) |
| `/files` | File management (auth required) |
| `/audit-logs` | Audit access records (auth required) |
| `/admin` | Admin panel (auth required) |
| `/community` | Education page |
| `/team` | Development team page |

## Structure

- `src/components/securfile/` — UI migrated from SecurFile
- `src/api/` — Axios clients aligned with backend `/api/v1`
- `src/stores/` — Pinia auth/file state
- `src/composables/useTheme.ts` — Light/dark theme

## Environment

Copy `.env` and adjust if needed:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
