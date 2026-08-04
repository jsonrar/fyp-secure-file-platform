from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import REPO_ROOT, Settings


def test_relative_runtime_paths_do_not_depend_on_working_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    configured = Settings(
        _env_file=None,
        ENCRYPTED_FILE_DIR="backend/runtime/encrypted",
        TEMP_FILE_DIR="backend/runtime/temp",
    )

    assert configured.ENCRYPTED_FILE_DIR == REPO_ROOT / "backend/runtime/encrypted"
    assert configured.TEMP_FILE_DIR == REPO_ROOT / "backend/runtime/temp"


def test_database_url_handles_reserved_password_characters() -> None:
    configured = Settings(_env_file=None, DB_PASSWORD="p@ss:/word")

    assert configured.DATABASE_URL.password == "p@ss:/word"
    assert "p%40ss%3A%2Fword" in configured.DATABASE_URL.render_as_string(hide_password=False)


def test_production_rejects_development_security_defaults() -> None:
    with pytest.raises(ValidationError, match="Unsafe settings"):
        Settings(_env_file=None, APP_ENV="production", APP_DEBUG=False)


def test_settings_repr_redacts_secrets() -> None:
    configured = Settings(
        _env_file=None,
        SECRET_KEY="secret-value-that-must-not-be-rendered",
        DB_PASSWORD="database-password-that-must-not-be-rendered",
    )

    rendered = repr(configured)

    assert "secret-value-that-must-not-be-rendered" not in rendered
    assert "database-password-that-must-not-be-rendered" not in rendered


def test_auth_lifetimes_and_rsa_size_are_validated() -> None:
    with pytest.raises(ValidationError, match="shorter than the absolute session"):
        Settings(
            _env_file=None,
            ACCESS_TOKEN_EXPIRE_MINUTES=60,
            SESSION_ABSOLUTE_EXPIRE_HOURS=1,
        )

    with pytest.raises(ValidationError, match="2048, 3072, or 4096"):
        Settings(_env_file=None, USER_RSA_KEY_SIZE=2050)


def test_account_and_ip_login_limits_are_configured_independently() -> None:
    configured = Settings(_env_file=None)

    assert configured.AUTH_REFRESH_MIN_INTERVAL_SECONDS > 0
    assert configured.AUTH_PASSWORD_HASH_CONCURRENCY == 2
    assert configured.AUTH_LOGIN_ACCOUNT_MAX_FAILURES < configured.AUTH_LOGIN_IP_MAX_FAILURES
    assert configured.AUTH_LOGIN_ACCOUNT_BLOCK_SECONDS < configured.AUTH_LOGIN_IP_BLOCK_SECONDS
    assert configured.AUTH_REAUTH_ACCOUNT_MAX_FAILURES < configured.AUTH_REAUTH_IP_MAX_FAILURES

    with pytest.raises(ValidationError, match="must be greater than the account limit"):
        Settings(
            _env_file=None,
            AUTH_LOGIN_ACCOUNT_MAX_FAILURES=10,
            AUTH_LOGIN_IP_MAX_FAILURES=10,
        )

    with pytest.raises(ValidationError, match="reauthentication account limit"):
        Settings(
            _env_file=None,
            AUTH_REAUTH_ACCOUNT_MAX_FAILURES=20,
            AUTH_REAUTH_IP_MAX_FAILURES=20,
        )
