from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.docker_client import DockerUnavailableError
from app.main import create_app


class FakeService:
    async def overview_payload(self) -> dict[str, Any]:
        return {
            "version": "01.00.00",
            "generated_at": "2026-03-26T00:00:00+00:00",
            "rows": [{"container_name": "web", "stack": "demo"}],
        }

    async def resources_payload(self) -> dict[str, Any]:
        return {"version": "01.00.00", "generated_at": "2026-03-26T00:00:00+00:00", "rows": []}

    async def ports_payload(self) -> dict[str, Any]:
        return {"version": "01.00.00", "generated_at": "2026-03-26T00:00:00+00:00", "rows": []}

    async def mounts_payload(self) -> dict[str, Any]:
        return {"version": "01.00.00", "generated_at": "2026-03-26T00:00:00+00:00", "rows": []}


class ErrorService(FakeService):
    async def overview_payload(self) -> dict[str, Any]:
        raise DockerUnavailableError("socket unavailable")


def _settings_with_auth(enabled: bool = False) -> Settings:
    env = {}
    if enabled:
        env = {
            "DOCUDOCKER_BASIC_AUTH_USER": "admin",
            "DOCUDOCKER_BASIC_AUTH_PASSWORD": "secret",
        }
    return load_settings(env=env)


def test_index_renders_version_and_repo_link() -> None:
    client = TestClient(create_app(settings=_settings_with_auth(False), service=FakeService()))
    response = client.get("/")
    assert response.status_code == 200
    assert "Running version 01.00.00" in response.text
    assert "https://github.com/paulkakell/docudock" in response.text


def test_api_route_returns_payload() -> None:
    client = TestClient(create_app(settings=_settings_with_auth(False), service=FakeService()))
    response = client.get("/api/overview")
    assert response.status_code == 200
    assert response.json()["rows"][0]["container_name"] == "web"


def test_basic_auth_blocks_unauthorized_requests() -> None:
    client = TestClient(create_app(settings=_settings_with_auth(True), service=FakeService()))
    response = client.get("/")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Basic")


def test_basic_auth_allows_valid_credentials() -> None:
    client = TestClient(create_app(settings=_settings_with_auth(True), service=FakeService()))
    response = client.get("/", auth=("admin", "secret"))
    assert response.status_code == 200


def test_security_headers_are_present() -> None:
    client = TestClient(create_app(settings=_settings_with_auth(False), service=FakeService()))
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_docker_error_maps_to_503() -> None:
    client = TestClient(create_app(settings=_settings_with_auth(False), service=ErrorService()))
    response = client.get("/api/overview")
    assert response.status_code == 503
    assert response.json()["detail"] == "Docker API unavailable"
