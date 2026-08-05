# Integration tests

[English](README.md) | [简体中文](README.zh-CN.md)

Database, repository, and storage integration tests belong here and must use a dedicated
disposable MySQL 8.4 database. Never point destructive fixtures at the normal development
database. Mark these tests with `@pytest.mark.integration` and add them with the first
database-backed vertical slice.
