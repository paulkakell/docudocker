from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings  # noqa: E402
from app.service import DockerDocumentationService  # noqa: E402


class SyntheticDockerClient:
    def __init__(self, container_count: int = 40) -> None:
        started_at = datetime.now(UTC) - timedelta(hours=6)
        self.containers = []
        self.inspect_payloads: dict[str, dict[str, Any]] = {}
        self.stats_payloads: dict[str, dict[str, Any]] = {}
        for index in range(container_count):
            container_id = f"container-{index:03d}"
            running = index % 5 != 0
            container = {
                "Id": container_id,
                "Names": [f"/service-{index:03d}"],
                "Image": f"example/service:{index % 7 + 1}.0.0",
                "Labels": {"com.docker.compose.project": f"stack-{index % 4}"},
                "State": "running" if running else "exited",
                "SizeRw": (index + 1) * 8192,
                "Ports": [{"PrivatePort": 8000 + index, "PublicPort": 9000 + index, "Type": "tcp"}],
                "Mounts": [
                    {
                        "Type": "bind",
                        "Destination": f"/data/{index}",
                        "Source": f"/srv/data/{index}",
                    }
                ],
                "NetworkSettings": {"Networks": {f"network-{index % 3}": {}}},
                "HostConfig": {"NetworkMode": f"network-{index % 3}"},
            }
            self.containers.append(container)
            self.inspect_payloads[container_id] = {
                "State": {
                    "Status": "running" if running else "exited",
                    "StartedAt": started_at.isoformat().replace("+00:00", "Z"),
                    "Health": {"Status": "healthy" if running else "none"},
                }
            }
            if running:
                self.stats_payloads[container_id] = {
                    "cpu_stats": {
                        "cpu_usage": {"total_usage": 200000000 + index, "percpu_usage": [1, 1]},
                        "system_cpu_usage": 2000000000 + index,
                        "online_cpus": 2,
                    },
                    "precpu_stats": {
                        "cpu_usage": {"total_usage": 100000000 + index},
                        "system_cpu_usage": 1000000000 + index,
                    },
                    "memory_stats": {
                        "usage": 134217728 + index,
                        "limit": 536870912,
                    },
                    "networks": {
                        f"network-{index % 3}": {
                            "rx_bytes": 1024 + index,
                            "tx_bytes": 2048 + index,
                        }
                    },
                }

    async def list_containers(self, include_size: bool = False) -> list[dict[str, Any]]:
        return self.containers

    async def inspect_container(self, container_id: str) -> dict[str, Any]:
        return self.inspect_payloads[container_id]

    async def container_stats(self, container_id: str) -> dict[str, Any]:
        return self.stats_payloads[container_id]


async def main() -> None:
    settings = load_settings()
    service = DockerDocumentationService(SyntheticDockerClient(), settings)

    async def measure(callable_name: str) -> float:
        started = perf_counter()
        await getattr(service, callable_name)()
        return round((perf_counter() - started) * 1000, 2)

    measurements: dict[str, list[float]] = {
        "get_overview_rows": [],
        "get_resource_rows": [],
        "get_port_rows": [],
        "get_mount_rows": [],
    }

    for callable_name in measurements:
        for _ in range(5):
            measurements[callable_name].append(await measure(callable_name))

    for callable_name, values in measurements.items():
        print(f"{callable_name}: mean={mean(values):.2f} ms runs={values}")


if __name__ == "__main__":
    asyncio.run(main())
