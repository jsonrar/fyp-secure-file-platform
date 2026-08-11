from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import provision_staging_test_accounts as provisioner


class SecretStorageTests(unittest.TestCase):
    def test_atomic_write_uses_restricted_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "credentials.json"

            provisioner.atomic_write(target, json.dumps({"example": True}))

            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"example": True})

    def test_secret_directory_is_rejected_inside_git_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            worktree = Path(temporary_directory)
            (worktree / ".git").mkdir()

            with self.assertRaisesRegex(provisioner.ProvisioningError, "Git worktree"):
                provisioner.ensure_secret_directory(worktree / "test-accounts")


class VerificationTests(unittest.TestCase):
    def test_verify_account_checks_login_role_and_logout(self) -> None:
        responses = (
            (200, {"data": {"access_token": "test-token"}}),
            (200, {"data": {"user": {"role": "ADMIN"}}}),
            (200, {"data": {"logged_out": True}}),
        )
        credentials = {"username": "admin", "password": "not-logged", "role": "ADMIN"}

        with patch.object(provisioner, "api_request", side_effect=responses) as request:
            provisioner.verify_account("http://127.0.0.1", credentials)

        self.assertEqual(
            [call.args[1] for call in request.call_args_list],
            ["/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/auth/logout"],
        )
        self.assertEqual(request.call_args_list[-1].kwargs["method"], "POST")
        self.assertEqual(request.call_args_list[-1].kwargs["token"], "test-token")

    def test_verify_account_logs_out_before_reporting_role_mismatch(self) -> None:
        responses = (
            (200, {"data": {"access_token": "test-token"}}),
            (200, {"data": {"user": {"role": "USER"}}}),
            (200, {"data": {"logged_out": True}}),
        )
        credentials = {"username": "admin", "password": "not-logged", "role": "ADMIN"}

        with (
            patch.object(provisioner, "api_request", side_effect=responses) as request,
            self.assertRaisesRegex(provisioner.ProvisioningError, "Role verification failed"),
        ):
            provisioner.verify_account("http://127.0.0.1", credentials)

        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args_list[-1].args[1], "/api/v1/auth/logout")


if __name__ == "__main__":
    unittest.main()
