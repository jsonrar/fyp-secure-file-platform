# Integration tests

[English](README.md) | [简体中文](README.zh-CN.md)

Database, repository, and storage integration tests belong here and must use a dedicated
disposable MySQL 8.4 database. Never point destructive fixtures at the normal development
database. Mark these tests with `@pytest.mark.integration` and add them with the first
database-backed vertical slice.

## Required MySQL 8.4 release gate

Run the complete isolated gate from the repository root:

```bash
./backend/tests/integration/run_mysql84_release_gate.sh
```

The runner creates a temporary Docker network, a fresh MySQL 8.4 server with a one-use CA
and hostname-verified TLS certificate, and randomly generated credentials. It exercises:

- empty database to Alembic head;
- a real `0001_initial -> 0002_auth_identity_sessions` upgrade;
- `alembic check` with no metadata drift;
- repeated provisioning, deployment, and verification without data loss;
- runtime denial and migration-account approval of DDL;
- unique, foreign-key, and delete-restrict constraints;
- active TLS 1.3 for runtime and migration connections, `REQUIRE SSL` accounts, and rejection
  of a connection that explicitly disables TLS; and
- every existing auth MySQL integration test with zero allowed skips.

The disposable database and accounts must use the `_test` and `mcs21_gate_` naming guards.
The runner destroys the test container, network, credentials, certificates, and databases
on exit. It never uses `.env` credentials or a normal development/staging database.

GitHub runs the same command through `.github/workflows/mysql84-release-gate.yml` for relevant
pull requests and pushes to `main`.

The latest recorded execution evidence is in the
[MySQL 8.4 Integration Test Report](../../../docs/MYSQL_8_4_INTEGRATION_TEST_REPORT.md).
