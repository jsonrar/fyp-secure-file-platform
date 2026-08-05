from __future__ import annotations

import argparse
import sys

from alembic import command
from alembic.util.exc import CommandError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from scripts.mysql_deployment import (
    DeploymentError,
    acquire_deployment_lock,
    classify_database,
    connect_with_retry,
    inspect_database,
    inspect_server,
    load_settings,
    migration_metadata,
    migration_url,
    release_deployment_lock,
    validate_audit_chain_head,
    validate_database_encoding,
    validate_head,
    validate_server,
)


def deploy(*, wait_timeout: float, lock_timeout: int, confirm_backup: bool) -> str:
    settings = load_settings()
    config, known_revisions, heads = migration_metadata()

    with connect_with_retry(
        migration_url(settings),
        wait_timeout,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        validate_server(inspect_server(connection))
        validate_database_encoding(inspect_database(connection, settings.DB_NAME))
        connection.commit()
        lock_name = acquire_deployment_lock(connection, settings, lock_timeout)
        try:
            before = inspect_database(connection, settings.DB_NAME)
            state = classify_database(before, known_revisions, heads)
            if state.needs_backup and not confirm_backup:
                raise DeploymentError(
                    f"database revision {state.current_revision!r} requires an upgrade; create "
                    "and verify a backup, then rerun with --confirm-backup"
                )
            if state.current_revision == "0001_initial":
                audit_count = int(connection.scalar(text("SELECT COUNT(*) FROM audit_logs")) or 0)
                if audit_count:
                    raise DeploymentError(
                        "revision 0001 contains audit rows and requires a reviewed adoption/"
                        "checkpoint migration"
                    )
            connection.commit()

            config.attributes["connection"] = connection
            command.upgrade(config, "head")

            after = inspect_database(connection, settings.DB_NAME)
            validate_database_encoding(after)
            head = validate_head(after, heads)
            validate_audit_chain_head(connection)
            connection.commit()
            command.check(config)
        finally:
            release_deployment_lock(connection, lock_name)

    print(f"MySQL schema is deployed at Alembic head {head!r}.")
    return head


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely upgrade a clean or Alembic-managed MySQL database to head."
    )
    parser.add_argument("--wait-timeout", type=float, default=60.0)
    parser.add_argument("--lock-timeout", type=int, default=60)
    parser.add_argument(
        "--confirm-backup",
        action="store_true",
        help="confirm that an existing managed database has a verified backup",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        deploy(
            wait_timeout=args.wait_timeout,
            lock_timeout=args.lock_timeout,
            confirm_backup=args.confirm_backup,
        )
    except (CommandError, DeploymentError, SQLAlchemyError) as exc:
        print(f"MySQL deployment failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
