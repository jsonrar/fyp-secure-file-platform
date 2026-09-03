from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NGINX_CONFIG = REPO_ROOT / "deployment/server/nginx-secureview.conf"


def _location(config: str, path: str) -> str:
    start = config.index(f"    location {path} {{")
    end = config.index("\n    }", start)
    return config[start:end]


def test_main_site_csp_remains_self_only() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")
    server_policy = config.split("    location ", maxsplit=1)[0]

    assert "script-src 'self' 'wasm-unsafe-eval'" in server_policy
    assert "cdn.jsdelivr.net" not in server_policy


def test_generated_api_docs_receive_only_the_assets_they_need() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")

    for path in ("/docs", "/redoc"):
        location = _location(config, path)
        assert "script-src 'unsafe-inline' https://cdn.jsdelivr.net" in location
        assert "style-src 'unsafe-inline' https://cdn.jsdelivr.net" in location
        assert "connect-src 'self'" in location
        assert "frame-ancestors 'none'" in location
        assert "X-Content-Type-Options nosniff" in location
        assert "Strict-Transport-Security" in location
        assert "X-Frame-Options DENY" in location
