from pathlib import Path

import pytest

from app.config import ConfigurationError, DockerMode, load_settings


def test_load_settings_defaults() -> None:
    settings = load_settings(env={}, explicit_root=Path(__file__).resolve().parent.parent)
    assert settings.version == "01.00.00"
    assert settings.docker_mode is DockerMode.SOCKET
    assert settings.auth_enabled is False
    assert settings.docker_api_base_url.endswith("/v1.43")


def test_load_settings_http_mode_validates_url() -> None:
    settings = load_settings(
        env={
            "DOCUDOCKER_DOCKER_MODE": "http",
            "DOCUDOCKER_DOCKER_BASE_URL": "http://docker-socket-proxy:2375",
        },
        explicit_root=Path(__file__).resolve().parent.parent,
    )
    assert settings.docker_mode is DockerMode.HTTP
    assert settings.docker_api_base_url == "http://docker-socket-proxy:2375/v1.43"


def test_load_settings_rejects_partial_basic_auth() -> None:
    with pytest.raises(ConfigurationError):
        load_settings(
            env={"DOCUDOCKER_BASIC_AUTH_USER": "admin"},
            explicit_root=Path(__file__).resolve().parent.parent,
        )


def test_load_settings_rejects_invalid_port() -> None:
    with pytest.raises(ConfigurationError):
        load_settings(
            env={"DOCUDOCKER_PORT": "70000"},
            explicit_root=Path(__file__).resolve().parent.parent,
        )
