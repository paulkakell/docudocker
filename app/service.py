from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from app.config import Settings
from app.docker_client import DockerUnavailableError
from app.formatters import (
    cpu_percent,
    derive_stack,
    format_uptime,
    health_status,
    humanize_bytes,
    memory_usage,
    network_names,
    network_usage,
    normalize_container_name,
    parse_release,
    title_case_status,
)
from app.models import MountRow, OverviewRow, PortRow, ResourceRow, build_table_payload

JsonMapping = Mapping[str, Any]


class DockerClientProtocol(Protocol):
    async def list_containers(self, include_size: bool = False) -> list[dict[str, Any]]: ...

    async def inspect_container(self, container_id: str) -> dict[str, Any]: ...

    async def container_stats(self, container_id: str) -> dict[str, Any]: ...


class DocumentationServiceProtocol(Protocol):
    async def overview_payload(self) -> dict[str, Any]: ...

    async def resources_payload(self) -> dict[str, Any]: ...

    async def ports_payload(self) -> dict[str, Any]: ...

    async def mounts_payload(self) -> dict[str, Any]: ...


class DockerDocumentationService:
    def __init__(self, docker_client: DockerClientProtocol, settings: Settings) -> None:
        self._docker_client = docker_client
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    def _container_name(self, container: JsonMapping) -> str:
        return normalize_container_name(
            container.get("Names"),
            str(container.get("Id", "")),
        )

    async def overview_payload(self) -> dict[str, Any]:
        rows = await self.get_overview_rows()
        return build_table_payload(self._settings.version, rows)

    async def resources_payload(self) -> dict[str, Any]:
        rows = await self.get_resource_rows()
        return build_table_payload(self._settings.version, rows)

    async def ports_payload(self) -> dict[str, Any]:
        rows = await self.get_port_rows()
        return build_table_payload(self._settings.version, rows)

    async def mounts_payload(self) -> dict[str, Any]:
        rows = await self.get_mount_rows()
        return build_table_payload(self._settings.version, rows)

    async def get_overview_rows(self) -> list[OverviewRow]:
        containers = await self._docker_client.list_containers()
        now = datetime.now(UTC)

        async def build_row(container: dict[str, Any]) -> OverviewRow:
            inspect_payload: dict[str, Any] = {}
            container_id = str(container.get("Id", ""))
            if container_id:
                try:
                    async with self._semaphore:
                        inspect_payload = await self._docker_client.inspect_container(container_id)
                except DockerUnavailableError as exc:
                    if exc.status_code != 404:
                        raise
            return self._overview_row(container, inspect_payload, now)

        rows = await asyncio.gather(*(build_row(container) for container in containers))
        return sorted(rows, key=lambda row: row.container_name.lower())

    async def get_resource_rows(self) -> list[ResourceRow]:
        containers = await self._docker_client.list_containers(include_size=True)

        async def build_row(container: dict[str, Any]) -> ResourceRow:
            stats_payload: dict[str, Any] = {}
            if str(container.get("State", "")).lower() == "running":
                container_id = str(container.get("Id", ""))
                if container_id:
                    try:
                        async with self._semaphore:
                            stats_payload = await self._docker_client.container_stats(container_id)
                    except DockerUnavailableError as exc:
                        if exc.status_code != 404:
                            raise
            return self._resource_row(container, stats_payload)

        rows = await asyncio.gather(*(build_row(container) for container in containers))
        return sorted(rows, key=lambda row: row.container_name.lower())

    async def get_port_rows(self) -> list[PortRow]:
        containers = await self._docker_client.list_containers()
        rows: list[PortRow] = []
        for container in containers:
            container_name = self._container_name(container)
            ports = container.get("Ports")
            if not isinstance(ports, list):
                continue
            network_value = network_names(container)
            normalized_ports = sorted(
                (item for item in ports if isinstance(item, dict)),
                key=lambda item: (
                    int(item.get("PrivatePort", 0) or 0),
                    int(item.get("PublicPort", 0) or 0),
                    str(item.get("Type", "")),
                ),
            )
            for port in normalized_ports:
                private_port = int(port.get("PrivatePort", 0) or 0)
                public_port = int(port.get("PublicPort", 0) or 0)
                protocol = str(port.get("Type", "tcp") or "tcp").lower()
                rows.append(
                    PortRow(
                        container_name=container_name,
                        network=network_value,
                        internal_port=f"{private_port}/{protocol}" if private_port else "-",
                        external_port=str(public_port) if public_port else "-",
                        internal_port_sort=private_port,
                        external_port_sort=public_port,
                    )
                )
        return sorted(
            rows,
            key=lambda row: (
                row.container_name.lower(),
                row.internal_port_sort,
                row.external_port_sort,
            ),
        )

    async def get_mount_rows(self) -> list[MountRow]:
        containers = await self._docker_client.list_containers()
        rows: list[MountRow] = []
        for container in containers:
            container_name = self._container_name(container)
            mounts = container.get("Mounts")
            if not isinstance(mounts, list):
                continue
            for mount in mounts:
                if not isinstance(mount, dict):
                    continue
                external_path = str(mount.get("Source") or mount.get("Name") or "-")
                rows.append(
                    MountRow(
                        container_name=container_name,
                        mount_type=str(mount.get("Type") or "-"),
                        internal_path=str(mount.get("Destination") or "-"),
                        external_path=external_path,
                    )
                )
        return sorted(
            rows,
            key=lambda row: (
                row.container_name.lower(),
                row.internal_path.lower(),
                row.external_path.lower(),
            ),
        )

    def _overview_row(
        self,
        container: JsonMapping,
        inspect_payload: JsonMapping,
        now: datetime,
    ) -> OverviewRow:
        labels = container.get("Labels")
        inspect_state = inspect_payload.get("State")
        if not isinstance(inspect_state, Mapping):
            inspect_state = None
        running_status_raw = None
        if isinstance(inspect_state, Mapping):
            running_status_raw = inspect_state.get("Status")
        if not isinstance(running_status_raw, str):
            running_status_raw = str(container.get("State") or "unknown")
        is_running = str(running_status_raw).lower() == "running"
        started_at = inspect_state.get("StartedAt") if isinstance(inspect_state, Mapping) else None
        uptime_display, uptime_sort = format_uptime(
            started_at if isinstance(started_at, str) else None,
            is_running=is_running,
            now=now,
        )
        label_mapping = labels if isinstance(labels, Mapping) else None
        stack = derive_stack(label_mapping if isinstance(label_mapping, Mapping) else None)
        image = str(container.get("Image") or "-")
        return OverviewRow(
            container_name=self._container_name(container),
            stack=stack,
            running_state=title_case_status(str(running_status_raw)),
            health_status=health_status(inspect_state),
            container_image=image,
            container_release=parse_release(image),
            uptime=uptime_display,
            uptime_sort=uptime_sort,
        )

    def _resource_row(self, container: JsonMapping, stats_payload: JsonMapping) -> ResourceRow:
        cpu_value = cpu_percent(stats_payload)
        memory_display, memory_sort = memory_usage(stats_payload)
        network_rx_display, network_rx_sort, network_tx_display, network_tx_sort = network_usage(
            stats_payload
        )
        disk_usage_raw = int(container.get("SizeRw", 0) or 0)
        return ResourceRow(
            container_name=self._container_name(container),
            current_cpu_usage=f"{cpu_value:.2f}%",
            current_memory_usage=memory_display,
            current_network_rx_usage=network_rx_display,
            current_network_tx_usage=network_tx_display,
            current_disk_usage=humanize_bytes(disk_usage_raw),
            cpu_sort=cpu_value,
            memory_sort=memory_sort,
            network_rx_sort=network_rx_sort,
            network_tx_sort=network_tx_sort,
            disk_sort=disk_usage_raw,
        )
