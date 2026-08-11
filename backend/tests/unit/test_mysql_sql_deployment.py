from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

import app.models  # noqa: F401 -- registers every model with Base.metadata
from app.core.database import Base

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MYSQL_SQL_ROOT = REPOSITORY_ROOT / "database" / "mysql"


def _read_sql(filename: str) -> str:
    return (MYSQL_SQL_ROOT / filename).read_text(encoding="utf-8")


def _permanent_table_blocks(schema_sql: str) -> dict[str, str]:
    return {
        match.group("table"): match.group("body")
        for match in re.finditer(
            r"CREATE TABLE\s+`?(?P<table>[a-z0-9_]+)`?\s*\("
            r"(?P<body>.*?)\)\s+ENGINE=InnoDB",
            schema_sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
    }


def _column_names(table_body: str) -> list[str]:
    columns: list[str] = []
    constraint_keywords = {"primary", "constraint", "foreign", "unique", "check", "on"}
    for line in table_body.splitlines():
        match = re.match(r"\s*`?([a-z][a-z0-9_]*)`?\s+", line, flags=re.IGNORECASE)
        if match is not None and match.group(1).lower() not in constraint_keywords:
            columns.append(match.group(1))
    return columns


def test_root_schema_sql_matches_application_metadata() -> None:
    schema_sql = _read_sql("02-schema.sql")
    table_blocks = _permanent_table_blocks(schema_sql)

    assert set(table_blocks) == {*Base.metadata.tables, "alembic_version"}
    for table in Base.metadata.sorted_tables:
        assert _column_names(table_blocks[table.name]) == [column.name for column in table.columns]
    assert _column_names(table_blocks["alembic_version"]) == ["version_num"]

    actual_indexes = {
        match.group("name"): (
            match.group("table"),
            tuple(column.strip().strip("`") for column in match.group("columns").split(",")),
        )
        for match in re.finditer(
            r"CREATE INDEX\s+(?P<name>[a-z0-9_]+)\s+"
            r"ON\s+`?(?P<table>[a-z0-9_]+)`?\s*\((?P<columns>[^)]+)\)",
            schema_sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
    }
    expected_indexes = {
        index.name: (table.name, tuple(column.name for column in index.columns))
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }
    assert actual_indexes == expected_indexes

    persistent_sql = schema_sql.split("DROP TEMPORARY TABLE fyp_schema_install_guard;", maxsplit=1)[
        1
    ]
    actual_named_constraints = {
        (match.group("name"), match.group("kind").upper())
        for match in re.finditer(
            r"CONSTRAINT\s+(?P<name>[a-z0-9_]+)\s+"
            r"(?P<kind>UNIQUE|FOREIGN KEY|CHECK|PRIMARY KEY)",
            persistent_sql,
            flags=re.IGNORECASE,
        )
    }
    expected_named_constraints: set[tuple[str, str]] = {("alembic_version_pkc", "PRIMARY KEY")}
    constraint_labels = {
        UniqueConstraint: "UNIQUE",
        ForeignKeyConstraint: "FOREIGN KEY",
        CheckConstraint: "CHECK",
    }
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            for constraint_type, label in constraint_labels.items():
                if isinstance(constraint, constraint_type) and constraint.name is not None:
                    expected_named_constraints.add((constraint.name, label))
                    break

    assert actual_named_constraints == expected_named_constraints


def test_root_schema_sql_is_empty_only_and_marks_completion_last() -> None:
    schema_sql = _read_sql("02-schema.sql")
    lowered = schema_sql.lower()

    assert "create table if not exists" not in lowered
    assert "insert ignore" not in lowered
    assert "on duplicate key" not in lowered
    assert "foreign_key_checks" not in lowered
    assert "fyp_migrator" not in schema_sql
    assert "ON `fyp_secure_file_platform`.*" not in schema_sql
    assert len(re.findall(r"(?m)^GRANT ", schema_sql)) == 13
    assert schema_sql.index("INSERT INTO audit_chain_heads") < schema_sql.index("GRANT SELECT")
    assert schema_sql.index("GRANT SELECT") < schema_sql.index("CREATE TABLE alembic_version")
    assert schema_sql.rstrip().endswith("VALUES ('0002_auth_identity_sessions');")


def test_root_verification_sql_is_read_only_and_checks_retired_identity() -> None:
    verification_sql = _read_sql("03-verify.sql")
    uncommented = "\n".join(
        line for line in verification_sql.splitlines() if not line.lstrip().startswith("--")
    )
    statements = [statement.strip() for statement in uncommented.split(";") if statement.strip()]

    assert statements
    assert all(statement.upper().startswith(("SELECT", "WITH")) for statement in statements)
    assert "mysql.global_grants" in verification_sql
    assert "fyp_migrator" in verification_sql
    assert "expected_table_grants" in verification_sql
