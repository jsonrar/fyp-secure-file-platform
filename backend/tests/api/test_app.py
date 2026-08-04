from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_liveness_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_schema_can_be_generated() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/auth/login" in response.json()["paths"]


def test_draft_business_routes_fail_closed() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/admin/users")

    assert response.status_code == 501
    assert response.json()["data"]["error_code"] == "feature_not_implemented"
    assert "access_token" not in response.text


def test_application_factory_accepts_isolated_settings() -> None:
    configured = Settings(
        _env_file=None,
        APP_NAME="Architecture Test API",
        APP_VERSION="9.9.9",
        API_PREFIX="/test/v1",
        DB_NAME="auth_isolation_test",
    )

    application = create_app(configured)

    assert application.title == "Architecture Test API"
    assert application.version == "9.9.9"
    assert application.state.settings is configured
    assert application.state.db_engine.url.database == "auth_isolation_test"
    assert application.state.db_session_factory.kw["bind"] is application.state.db_engine
    assert (
        application.state.password_manager.max_concurrent_operations
        == configured.AUTH_PASSWORD_HASH_CONCURRENCY
    )
    assert "/test/v1/auth/login" in application.openapi()["paths"]
