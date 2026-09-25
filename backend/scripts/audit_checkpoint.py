"""Publish and independently verify HMAC audit-chain checkpoints.

A checkpoint contains only the audit-chain head, schema revision, and UTC time. It never
contains audit descriptions, usernames, filenames, tokens, key material, or file content.
The HMAC key is supplied only through ``AUDIT_CHECKPOINT_HMAC_KEY`` and is never printed.

Production usage is documented in docs/OBSERVABILITY_AND_INCIDENT_RESPONSE.md.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymysql

FORMAT_VERSION = 1
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_CHECKPOINT_RE = re.compile(r"^audit-checkpoint-\d{8}T\d{6}Z-[0-9]+\.json$")


class CheckpointError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DbConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_ca: str | None


def _db_config_from_env() -> DbConfig:
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    if not user or not password:
        raise CheckpointError("DB_USER and DB_PASSWORD must be set")
    return DbConfig(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "fyp_secure_file_platform"),
        user=user,
        password=password,
        ssl_ca=os.getenv("DB_SSL_CA") or None,
    )


def _checkpoint_key() -> bytes:
    raw = os.getenv("AUDIT_CHECKPOINT_HMAC_KEY", "")
    if len(raw.encode("utf-8")) < 32:
        raise CheckpointError("AUDIT_CHECKPOINT_HMAC_KEY must contain at least 32 bytes")
    return raw.encode("utf-8")


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_payload(payload: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()


def build_record(
    *,
    last_log_id: int | None,
    current_hash: str,
    schema_revision: str,
    created_at: datetime,
    key: bytes,
) -> dict[str, Any]:
    if not _HASH_RE.fullmatch(current_hash):
        raise CheckpointError("audit chain head is not a lowercase SHA-256 value")
    created = created_at.astimezone(UTC).replace(microsecond=0)
    payload: dict[str, Any] = {
        "format": FORMAT_VERSION,
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
        "last_log_id": last_log_id,
        "current_hash": current_hash,
        "schema_revision": schema_revision,
    }
    return {"payload": payload, "hmac_sha256": sign_payload(payload, key)}


def verify_record(record: dict[str, Any], key: bytes) -> dict[str, Any]:
    payload = record.get("payload")
    signature = record.get("hmac_sha256")
    if not isinstance(payload, dict) or not isinstance(signature, str):
        raise CheckpointError("checkpoint must contain payload and hmac_sha256")
    if payload.get("format") != FORMAT_VERSION:
        raise CheckpointError("unsupported checkpoint format")
    current_hash = payload.get("current_hash")
    if not isinstance(current_hash, str) or not _HASH_RE.fullmatch(current_hash):
        raise CheckpointError("checkpoint current_hash is invalid")
    last_log_id = payload.get("last_log_id")
    if last_log_id is not None and (not isinstance(last_log_id, int) or last_log_id < 1):
        raise CheckpointError("checkpoint last_log_id is invalid")
    schema_revision = payload.get("schema_revision")
    if not isinstance(schema_revision, str) or not schema_revision:
        raise CheckpointError("checkpoint schema_revision is invalid")
    created_at = payload.get("created_at_utc")
    if not isinstance(created_at, str):
        raise CheckpointError("checkpoint created_at_utc is invalid")
    try:
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CheckpointError("checkpoint created_at_utc is invalid") from exc
    expected = sign_payload(payload, key)
    if not hmac.compare_digest(signature, expected):
        raise CheckpointError("checkpoint HMAC verification failed")
    return payload


def _connect(config: DbConfig) -> pymysql.connections.Connection:
    kwargs: dict[str, Any] = {
        "host": config.host,
        "port": config.port,
        "user": config.user,
        "password": config.password,
        "database": config.database,
        "connect_timeout": 10,
    }
    if config.ssl_ca:
        kwargs.update(
            {
                "ssl_ca": config.ssl_ca,
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
            }
        )
    return pymysql.connect(**kwargs)


def read_chain_head(config: DbConfig) -> tuple[int | None, str, str]:
    connection = _connect(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT last_log_id, current_hash, schema_revision "
                "FROM audit_chain_heads WHERE id = 1"
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    if row is None:
        raise CheckpointError("audit chain head row is missing")
    last_log_id, current_hash, schema_revision = row
    return (
        int(last_log_id) if last_log_id is not None else None,
        str(current_hash),
        str(schema_revision),
    )


def _write_record(out_dir: Path, record: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(out_dir, 0o700)
    payload = record["payload"]
    stamp = str(payload["created_at_utc"]).replace("-", "").replace(":", "")
    last_log_id = payload["last_log_id"] or 0
    filename = f"audit-checkpoint-{stamp}-{last_log_id}.json"
    final = out_dir / filename
    if final.exists():
        raise CheckpointError(f"checkpoint already exists: {filename}")
    fd, temporary_name = tempfile.mkstemp(prefix=".checkpoint-", dir=out_dir)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        temporary.replace(final)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return final


def publish_file(path: Path, dest: str) -> str:
    """Publish one already-signed checkpoint; credentials stay in the environment."""

    target_name = path.name
    if dest.startswith("s3://"):
        aws = shutil.which("aws")
        if not aws:
            raise CheckpointError("destination is s3:// but the aws CLI is not installed")
        command = [
            aws,
            "s3",
            "cp",
            "--only-show-errors",
            str(path),
            f"{dest.rstrip('/')}/{target_name}",
        ]
        endpoint = os.getenv("AUDIT_CHECKPOINT_S3_ENDPOINT_URL") or os.getenv(
            "BACKUP_S3_ENDPOINT_URL"
        )
        if endpoint:
            command += ["--endpoint-url", endpoint]
        subprocess.run(command, check=True)
        return f"{dest.rstrip('/')}/{target_name}"
    if re.match(r"^[^/]+@[^/:]+:", dest):
        rsync = shutil.which("rsync")
        if not rsync:
            raise CheckpointError("destination is remote but rsync is not installed")
        target = f"{dest.rstrip('/')}/{target_name}"
        subprocess.run([rsync, "--chmod=F600", str(path), target], check=True)
        return target
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    final = root / target_name
    if final.exists():
        raise CheckpointError(f"checkpoint already exists at destination: {target_name}")
    shutil.copyfile(path, final)
    os.chmod(final, 0o600)
    return str(final)


def publish_checkpoint(out_dir: Path, dest: str | None) -> tuple[Path, str | None]:
    config = _db_config_from_env()
    key = _checkpoint_key()
    last_log_id, current_hash, schema_revision = read_chain_head(config)
    record = build_record(
        last_log_id=last_log_id,
        current_hash=current_hash,
        schema_revision=schema_revision,
        created_at=datetime.now(UTC),
        key=key,
    )
    path = _write_record(out_dir, record)
    location = publish_file(path, dest) if dest else None
    return path, location


def _checkpoint_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise CheckpointError(f"checkpoint path does not exist: {path}")
    return sorted(
        item for item in path.iterdir() if item.is_file() and _CHECKPOINT_RE.match(item.name)
    )


def verify_path(path: Path) -> int:
    key = _checkpoint_key()
    checkpoints = _checkpoint_paths(path)
    if not checkpoints:
        raise CheckpointError("no audit checkpoints found")
    previous_log_id = -1
    previous_created: datetime | None = None
    for checkpoint in checkpoints:
        try:
            record = json.loads(checkpoint.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CheckpointError(f"cannot parse checkpoint {checkpoint.name}") from exc
        payload = verify_record(record, key)
        log_id = int(payload["last_log_id"] or 0)
        created_text = str(payload["created_at_utc"])
        created = datetime.fromisoformat(created_text.replace("Z", "+00:00"))
        if log_id < previous_log_id:
            raise CheckpointError("checkpoint last_log_id moved backwards")
        if previous_created is not None and created < previous_created:
            raise CheckpointError("checkpoint time moved backwards")
        previous_log_id = log_id
        previous_created = created
    print(json.dumps({"verified": len(checkpoints), "last_log_id": previous_log_id}))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--publish",
        action="store_true",
        help="read the live chain head and sign it",
    )
    group.add_argument(
        "--verify",
        metavar="PATH",
        help="verify one checkpoint or a directory",
    )
    parser.add_argument(
        "--out-dir",
        default=os.getenv("AUDIT_CHECKPOINT_DIR", "audit_checkpoints"),
        help="local checkpoint directory",
    )
    parser.add_argument(
        "--dest",
        default=os.getenv("AUDIT_CHECKPOINT_DEST") or None,
        help="optional local, user@host:/path, or s3:// external destination",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.verify:
            return verify_path(Path(args.verify))
        path, location = publish_checkpoint(Path(args.out_dir), args.dest)
        print(
            json.dumps(
                {
                    "checkpoint": path.name,
                    "published": location is not None,
                    "destination": location,
                }
            )
        )
        return 0
    except (CheckpointError, OSError, pymysql.MySQLError) as exc:
        print(f"audit_checkpoint: FAILED -- {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        program = exc.cmd[0] if isinstance(exc.cmd, list) else str(exc.cmd)
        print(f"audit_checkpoint: FAILED -- {program} exited {exc.returncode}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
