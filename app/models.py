from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class OverviewRow:
    container_name: str
    stack: str
    running_state: str
    health_status: str
    container_image: str
    container_release: str
    uptime: str
    uptime_sort: int


@dataclass(frozen=True)
class ResourceRow:
    container_name: str
    current_cpu_usage: str
    current_memory_usage: str
    current_network_rx_usage: str
    current_network_tx_usage: str
    current_disk_usage: str
    cpu_sort: float
    memory_sort: int
    network_rx_sort: int
    network_tx_sort: int
    disk_sort: int


@dataclass(frozen=True)
class PortRow:
    container_name: str
    network: str
    internal_port: str
    external_port: str
    internal_port_sort: int
    external_port_sort: int


@dataclass(frozen=True)
class MountRow:
    container_name: str
    mount_type: str
    internal_path: str
    external_path: str


RowType = OverviewRow | ResourceRow | PortRow | MountRow


def build_table_payload(version: str, rows: Sequence[RowType]) -> dict[str, Any]:
    serialized_rows = [vars(row).copy() for row in rows]
    return {
        "version": version,
        "generated_at": datetime.now(UTC).isoformat(),
        "rows": serialized_rows,
    }
