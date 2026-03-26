from __future__ import annotations

from typing import Any

import httpx

from app.config import DockerMode, Settings

JsonDict = dict[str, Any]


class DockerUnavailableError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DockerClient:
    def __init__(self, settings: Settings) -> None:
        transport: httpx.AsyncBaseTransport | None = None
        if settings.docker_mode is DockerMode.SOCKET:
            transport = httpx.AsyncHTTPTransport(uds=settings.docker_socket_path)

        limits = httpx.Limits(
            max_connections=settings.max_concurrency + 2,
            max_keepalive_connections=settings.max_concurrency + 2,
        )
        timeout = httpx.Timeout(settings.docker_timeout_seconds)

        self._client = httpx.AsyncClient(
            base_url=settings.docker_api_base_url,
            headers={"Accept": "application/json"},
            limits=limits,
            timeout=timeout,
            transport=transport,
            trust_env=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_json(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DockerUnavailableError(
                f"Docker API returned {exc.response.status_code} for {path}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise DockerUnavailableError(f"Docker API request failed for {path}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise DockerUnavailableError(f"Docker API returned invalid JSON for {path}") from exc

    async def list_containers(self, include_size: bool = False) -> list[JsonDict]:
        params = {"all": "1"}
        if include_size:
            params["size"] = "1"
        payload = await self._get_json("/containers/json", params=params)
        if not isinstance(payload, list):
            raise DockerUnavailableError("Docker API returned an unexpected containers payload")
        return [item for item in payload if isinstance(item, dict)]

    async def inspect_container(self, container_id: str) -> JsonDict:
        payload = await self._get_json(f"/containers/{container_id}/json")
        if not isinstance(payload, dict):
            raise DockerUnavailableError(
                f"Docker inspect payload for {container_id} was not an object"
            )
        return payload

    async def container_stats(self, container_id: str) -> JsonDict:
        payload = await self._get_json(
            f"/containers/{container_id}/stats",
            params={"stream": "false"},
        )
        if not isinstance(payload, dict):
            raise DockerUnavailableError(
                f"Docker stats payload for {container_id} was not an object"
            )
        return payload
