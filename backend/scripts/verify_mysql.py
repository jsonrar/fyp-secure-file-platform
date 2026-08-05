from __future__ import annotations

import argparse
import sys

from alembic import command
from alembic.util.exc import CommandError
from sqlalchemy.exc import SQLAlchemyError

from scripts.mysql_deployment import (
    DeploymentError,
    acquire_deployment_lock,
    application_url,
    connect_with_retry,
    inspect_database,
    inspect_server,
    load_settings,
    migration_metadata,
    release_deployment_lock,
    validate_audit_chain_head,
    validate_database_encoding,
    validate_head,
    validate_server,
)


def verify(*, wait_timeout: float, lock_timeout: int) -> str:
    settings = load_settings()
    config, _, heads = migration_metadata()

    with connect_with_retry(
        application_url(settings),
        wait_timeout,
        connect_args=settings.DATABASE_CONNECT_ARGS,
    ) as connection:
        validate_server(inspect_server(connection))
        connection.commit()
        lock_name = acquire_deployment_lock(connection, settings, lock_timeout)
        try:
            snapshot = inspect_database(connection, settings.DB_NAME)
            validate_database_encoding(snapshot)
            head = validate_head(snapshot, heads)
            validate_audit_chain_head(connection)
            connection.commit()
            config.attributes["connection"] = connection
            command.check(config)
        finally:
            release_deployment_lock(connection, lock_name)

    print(f"MySQL deployment verified at Alembic head {head!r}.")
    return head


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify MySQL version, schema ownership, Alembic head, and metadata drift."
    )
    parser.add_argument("--wait-timeout", type=float, default=30.0)
    parser.add_argument("--lock-timeout", type=int, default=30)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        verify(wait_timeout=args.wait_timeout, lock_timeout=args.lock_timeout)
    except (CommandError, DeploymentError, SQLAlchemyError) as exc:
        print(f"MySQL verification failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
