from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse


class DockerMode(StrEnum):
    SOCKET = "socket"
    HTTP = "http"


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    version: str
    github_url: str
    host: str
    port: int
    docker_mode: DockerMode
    docker_socket_path: str
    docker_base_url: str
    docker_api_version: str
    docker_timeout_seconds: float
    max_concurrency: int
    basic_auth_user: str | None
    basic_auth_password: str | None
    log_level: str

    @property
    def auth_enabled(self) -> bool:
        return bool(self.basic_auth_user and self.basic_auth_password)

    @property
    def docker_api_base_url(self) -> str:
        if self.docker_mode is DockerMode.SOCKET:
            return f"http://docker/{self.docker_api_version}"
        normalized = self.docker_base_url.rstrip("/")
        if normalized.endswith(f"/{self.docker_api_version}"):
            return normalized
        return f"{normalized}/{self.docker_api_version}"


def _project_root(explicit_root: Path | None = None) -> Path:
    return explicit_root or Path(__file__).resolve().parent.parent


def _read_version(explicit_root: Path | None = None) -> str:
    version_path = _project_root(explicit_root) / "VERSION"
    return version_path.read_text(encoding="utf-8").strip()


def _parse_int(raw_value: str, name: str) -> int:
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


def _parse_float(raw_value: str, name: str) -> float:
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc


def _normalize_log_level(raw_value: str) -> str:
    allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    normalized = raw_value.upper()
    if normalized not in allowed:
        raise ConfigurationError(
            "DOCUDOCKER_LOG_LEVEL must be one of CRITICAL, ERROR, "
            "WARNING, INFO, DEBUG"
        )
    return normalized


def load_settings(
    env: Mapping[str, str] | None = None,
    explicit_root: Path | None = None,
) -> Settings:
    data = env if env is not None else os.environ

    version = data.get("DOCUDOCKER_VERSION") or _read_version(explicit_root)
    github_url = data.get(
        "DOCUDOCKER_GITHUB_URL",
        "https://github.com/paulkakell/docudock",
    )

    host = data.get("DOCUDOCKER_HOST", "127.0.0.1")
    port = _parse_int(data.get("DOCUDOCKER_PORT", "8080"), "DOCUDOCKER_PORT")
    if not 1 <= port <= 65535:
        raise ConfigurationError("DOCUDOCKER_PORT must be between 1 and 65535")

    docker_mode_raw = data.get("DOCUDOCKER_DOCKER_MODE", DockerMode.SOCKET).lower()
    try:
        docker_mode = DockerMode(docker_mode_raw)
    except ValueError as exc:
        raise ConfigurationError("DOCUDOCKER_DOCKER_MODE must be 'socket' or 'http'") from exc

    docker_socket_path = data.get("DOCUDOCKER_DOCKER_SOCKET_PATH", "/var/run/docker.sock")
    docker_base_url = data.get("DOCUDOCKER_DOCKER_BASE_URL", "http://docker-socket-proxy:2375")
    parsed_url = urlparse(docker_base_url)
    if docker_mode is DockerMode.HTTP and not (parsed_url.scheme and parsed_url.netloc):
        raise ConfigurationError(
            "DOCUDOCKER_DOCKER_BASE_URL must be a valid absolute URL in http mode"
        )

    docker_api_version_raw = data.get("DOCUDOCKER_DOCKER_API_VERSION", "v1.43").strip()
    docker_api_version = (
        docker_api_version_raw
        if docker_api_version_raw.startswith("v")
        else f"v{docker_api_version_raw}"
    )

    docker_timeout_seconds = _parse_float(
        data.get("DOCUDOCKER_DOCKER_TIMEOUT_SECONDS", "5.0"),
        "DOCUDOCKER_DOCKER_TIMEOUT_SECONDS",
    )
    if docker_timeout_seconds <= 0:
        raise ConfigurationError("DOCUDOCKER_DOCKER_TIMEOUT_SECONDS must be greater than zero")

    max_concurrency = _parse_int(
        data.get("DOCUDOCKER_MAX_CONCURRENCY", "4"),
        "DOCUDOCKER_MAX_CONCURRENCY",
    )
    if max_concurrency < 1:
        raise ConfigurationError("DOCUDOCKER_MAX_CONCURRENCY must be at least 1")

    basic_auth_user = data.get("DOCUDOCKER_BASIC_AUTH_USER") or None
    basic_auth_password = data.get("DOCUDOCKER_BASIC_AUTH_PASSWORD") or None
    if bool(basic_auth_user) ^ bool(basic_auth_password):
        raise ConfigurationError(
            "DOCUDOCKER_BASIC_AUTH_USER and "
            "DOCUDOCKER_BASIC_AUTH_PASSWORD must both be set or both be omitted"
        )

    log_level = _normalize_log_level(data.get("DOCUDOCKER_LOG_LEVEL", "INFO"))

    return Settings(
        version=version,
        github_url=github_url,
        host=host,
        port=port,
        docker_mode=docker_mode,
        docker_socket_path=docker_socket_path,
        docker_base_url=docker_base_url,
        docker_api_version=docker_api_version,
        docker_timeout_seconds=docker_timeout_seconds,
        max_concurrency=max_concurrency,
        basic_auth_user=basic_auth_user,
        basic_auth_password=basic_auth_password,
        log_level=log_level,
    )
