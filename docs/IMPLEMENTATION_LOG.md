# Implementation Log

[English] | [简体中文](IMPLEMENTATION_LOG.zh-CN.md)

## 2026-08-11 — Database deployment and integration gate

**Contributor:** `Waldo0926`

### Merged record

- PR [#1](https://github.com/jsonrar/fyp-secure-file-platform/pull/1) merged into `main`.
- Merge commit: `181e50a42022095ead2a40af2c77b8b71778913d`.
- Fixed the MySQL 8.4 `0001 -> 0002` foreign-key index ordering failure.
- Normalized equivalent MySQL timestamp defaults for Alembic drift checks.
- Synchronized ORM timestamp defaults with the deployed schema.
- Removed the hard-coded administrator login and fake-token fallbacks.

### Current integration-test record

- Branch: `agent/mysql84-integration-tests`.
- Added a required GitHub Actions MySQL 8.4 release gate.
- Added disposable, name-guarded MySQL fixtures with zero permitted skips.
- Added real empty-schema, managed-upgrade, repeat-deployment, privilege, constraint, and
  verified-TLS tests.
- Added a reproducible Docker runner that creates and destroys all test infrastructure.
- Recorded the final evidence in
  [MySQL 8.4 Integration Test Report](MYSQL_8_4_INTEGRATION_TEST_REPORT.md).
