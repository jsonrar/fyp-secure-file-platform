#!/usr/bin/env python3
"""Provision reusable staging accounts without printing their secrets.

Run this script on the deployment host. It registers accounts through the
public application API, sets their application roles inside the backend
container, verifies login and ``/auth/me``, and stores passwords/private keys
in a root-only directory outside the repository.

The script deliberately fails closed when an account already exists but its
saved credentials are missing. It never resets an unknown password.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_ACCOUNTS = (
    {"username": "admin", "email": "admin@mcs21-test.example.com", "role": "ADMIN"},
    {"username": "test_user_1", "email": "user1@mcs21-test.example.com", "role": "USER"},
    {"username": "test_user_2", "email": "user2@mcs21-test.example.com", "role": "USER"},
)


class ProvisioningError(RuntimeError):
    """Raised when an account cannot be provisioned or verified safely."""


def api_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        raw_body = error.read()
        try:
            parsed_body = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed_body = {"message": "Non-JSON error response"}
        return error.code, parsed_body


def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_secret_directory(output_dir: Path) -> None:
    if not output_dir.is_absolute():
        raise ProvisioningError("The secret output directory must be an absolute path")
    for candidate in (output_dir, *output_dir.parents):
        if (candidate / ".git").exists():
            raise ProvisioningError("Refusing to store test credentials inside a Git worktree")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)


def load_credentials(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    accounts = payload.get("accounts")
    if not isinstance(accounts, dict):
        raise ProvisioningError(f"Invalid credentials file: {path}")
    return accounts


def save_credentials(path: Path, accounts: dict[str, dict[str, str]]) -> None:
    atomic_write(path, json.dumps({"accounts": accounts}, indent=2) + "\n")


def register_account(
    *,
    base_url: str,
    account: dict[str, str],
    output_dir: Path,
) -> dict[str, str]:
    password = f"M21-{secrets.token_urlsafe(24)}-Aa1!"
    status, response = api_request(
        base_url,
        "/api/v1/auth/register",
        method="POST",
        payload={
            "username": account["username"],
            "email": account["email"],
            "password": password,
        },
    )
    if status != 201:
        error_code = response.get("error", {}).get("code", "unknown_error")
        raise ProvisioningError(
            f"Registration failed for {account['username']}: HTTP {status} ({error_code})"
        )

    private_key = response.get("data", {}).get("private_key_pem")
    if not isinstance(private_key, str) or not private_key.startswith(
        "-----BEGIN PRIVATE KEY-----"
    ):
        raise ProvisioningError(f"Registration for {account['username']} returned no private key")

    private_key_path = output_dir / f"{account['username']}-private-key.pem"
    atomic_write(private_key_path, private_key)
    return {
        "username": account["username"],
        "email": account["email"],
        "password": password,
        "role": account["role"],
        "private_key_path": str(private_key_path),
    }


def set_database_role(container: str, username: str, role: str) -> None:
    code = (
        "import sys; "
        "from app.core.database import SessionLocal; "
        "from app.domain.enums import SystemRole; "
        "from app.models.user import User; "
        "db=SessionLocal(); "
        "user=db.query(User).filter(User.username == sys.argv[1]).one(); "
        "user.role=SystemRole(sys.argv[2]); "
        "db.commit(); db.close()"
    )
    result = subprocess.run(
        ["docker", "exec", container, "python", "-c", code, username, role],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ProvisioningError(
            f"Role update failed for {username} (docker exec exit {result.returncode})"
        )


def verify_account(base_url: str, credentials: dict[str, str]) -> None:
    login_status, login = api_request(
        base_url,
        "/api/v1/auth/login",
        method="POST",
        payload={
            "username": credentials["username"],
            "password": credentials["password"],
        },
    )
    if login_status != 200:
        raise ProvisioningError(
            f"Login verification failed for {credentials['username']}: HTTP {login_status}"
        )
    access_token = login.get("data", {}).get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ProvisioningError(f"Login for {credentials['username']} returned no access token")

    me_status, me = api_request(base_url, "/api/v1/auth/me", token=access_token)
    logout_status, _ = api_request(
        base_url,
        "/api/v1/auth/logout",
        method="POST",
        token=access_token,
    )
    if logout_status != 200:
        raise ProvisioningError(
            f"Logout verification failed for {credentials['username']}: HTTP {logout_status}"
        )

    user = me.get("data", {}).get("user", {})
    if me_status != 200 or user.get("role") != credentials["role"]:
        raise ProvisioningError(
            f"Role verification failed for {credentials['username']}: "
            f"expected {credentials['role']}, got {user.get('role')}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1")
    parser.add_argument("--container", default="mcs21-staging-backend-1")
    parser.add_argument("--output-dir", type=Path, default=Path("/srv/mcs21/test-accounts"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.umask(0o077)
    ensure_secret_directory(args.output_dir)
    credentials_path = args.output_dir / "credentials.json"
    credentials = load_credentials(credentials_path)

    health_status, _ = api_request(args.base_url, "/health")
    if health_status != 200:
        raise ProvisioningError(f"Application health check failed: HTTP {health_status}")

    for account in DEFAULT_ACCOUNTS:
        username = account["username"]
        saved = credentials.get(username)
        if saved is None:
            saved = register_account(
                base_url=args.base_url,
                account=account,
                output_dir=args.output_dir,
            )
            credentials[username] = saved
            save_credentials(credentials_path, credentials)
            print(f"{username}: registered")
        else:
            if saved.get("email") != account["email"]:
                raise ProvisioningError(f"Stored email mismatch for {username}")
            private_key_path = Path(saved.get("private_key_path", ""))
            if not private_key_path.is_file():
                raise ProvisioningError(f"Stored private key is missing for {username}")
            saved["role"] = account["role"]
            print(f"{username}: using stored credentials")

        set_database_role(args.container, username, account["role"])
        verify_account(args.base_url, saved)
        print(f"{username}: login, role, and logout verified ({account['role']})")

    save_credentials(credentials_path, credentials)
    print(f"credentials: {credentials_path} (mode 0600)")
    print("private keys: stored separately in the same directory (mode 0600)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProvisioningError as error:
        print(f"Provisioning failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
