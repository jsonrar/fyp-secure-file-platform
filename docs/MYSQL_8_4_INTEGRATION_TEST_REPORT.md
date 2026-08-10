# MySQL 8.4 Integration Test Report

[English] | [简体中文](MYSQL_8_4_INTEGRATION_TEST_REPORT.zh-CN.md)

## Result

- **Status:** PASS
- **Executed by:** `Waldo0926`
- **Date:** 2026-08-11
- **Final run:** 04:04:59-04:05:45 Asia/Kuala_Lumpur
- **Source branch:** `agent/mysql84-integration-tests`, based on merge commit `181e50a`
- **Environment:** isolated Docker network on the project VPS; `mysql:8.4` and Python 3.12.13
- **Data boundary:** no staging database, account, credential, or application data was used

The runner generated one-use credentials, a one-use certificate authority, and a server
certificate valid only for the disposable `mysql84-gate` hostname. The CA private key was not
mounted into either test container. The MySQL container,
network, databases, accounts, credentials, certificates, and test image were removed when the
run finished.

## Final evidence

| Check | Result |
|---|---|
| Ruff over application, migrations, scripts, and tests | Passed |
| API and unit tests | `108 passed, 14 deselected` in 7.16 s |
| Real MySQL 8.4 integration tests | `14 passed, 108 deselected` in 4.58 s |
| Skipped tests in the required integration gate | `0` |
| Empty database to Alembic head | Passed at `0002_auth_identity_sessions` |
| Real `0001_initial -> 0002_auth_identity_sessions` upgrade | Passed |
| Backup-confirmation refusal before managed upgrade | Passed |
| `alembic check` metadata drift | No drift |
| Repeated provision/deploy/verify | Passed; sentinel row and table set preserved |
| Runtime account DDL | Correctly denied |
| Migration account DDL | Correctly permitted |
| Unique, foreign-key, and delete-restrict constraints | Passed |
| Runtime and migration TLS | Verified TLS 1.3 with certificate and hostname validation |
| Accounts and insecure transport | `REQUIRE SSL`; explicit non-TLS connection rejected |

## Correction log

1. The first infrastructure run stopped before tests because a macOS archive included
   AppleDouble `._*` metadata files. A repository `.dockerignore` now excludes these files so
   Mac-created contexts are safe on Linux.
2. The next run reached the database and reported `118 passed, 4 failed`. Three failures came
   from passing CI TLS environment variables into unit tests that intentionally construct
   development settings. Unit and integration phases are now isolated. The fourth confirmed
   that MySQL rejected a non-TLS login but used error 1045 rather than 3159; the assertion now
   accepts both documented secure refusal forms after proving the same credentials succeed
   with verified TLS 1.3.
3. The final run passed all 122 selected tests across the isolated unit and integration
   phases, with no integration skips.

## Reproduction

From the repository root on a Docker host:

```bash
./backend/tests/integration/run_mysql84_release_gate.sh
```

GitHub runs the same command through `.github/workflows/mysql84-release-gate.yml` for relevant
pull requests and pushes to `main`.
