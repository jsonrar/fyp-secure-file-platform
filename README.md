# Secure File Encryption and Sharing Platform

Final Year Project starter architecture for a secure file encryption and sharing platform.

## Project Goal

This system allows users to upload files, store them encrypted on the server, share files with other authorised users, revoke future access, verify file integrity, and record sensitive actions in an audit log.

The project focuses on:

- Server-side AES file encryption
- RSA-based file key wrapping
- Controlled sharing and revocation
- Role-based and file-level access control
- SHA-256 integrity verification
- Tamper-evident audit log using hash chaining
- Recovery governance for exceptional access cases

## Recommended Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | FastAPI |
| Database | MySQL |
| File Storage | Local encrypted file storage for FYP demo |
| File Encryption | AES-256-GCM |
| Key Wrapping | RSA-OAEP with SHA-256 |
| Password Hashing | bcrypt / Argon2 |

## Repository Structure

```text
fyp-secure-file-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── encrypted_files/
│   ├── temp_files/
│   ├── logs/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── router/
│   │   └── stores/
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_DESIGN.md
│   ├── DATABASE_SCHEMA.md
│   ├── SECURITY_FLOWS.md
│   └── PROJECT_SCOPE.md
├── .env.example
├── .gitignore
└── docker-compose.yml
```

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger:

```text
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open frontend:

```text
http://localhost:5173
```

## Git Push Suggestion

Do not push the zip file itself. Extract this folder, then run:

```bash
cd fyp-secure-file-platform
git init
git add .
git commit -m "Initial FYP project architecture scaffold"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

## Important Security Note

This starter project is an architecture scaffold. The cryptographic flow is designed for an FYP prototype and demonstration. For production deployment, key management should be strengthened using KMS/HSM, hardened server configuration, secure key custody procedures, formal audit approval workflows, and professional security review.
