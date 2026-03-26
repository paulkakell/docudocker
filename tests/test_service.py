import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import load_settings
from app.service import DockerDocumentationService


class FakeDockerClient:
    def __init__(self) -> None:
        started_at = datetime.now(UTC) - timedelta(hours=2)
        self.containers = [
            {
                "Id": "abc123def456",
                "Names": ["/web"],
                "Image": "nginx:1.25.4",
                "Labels": {"com.docker.compose.project": "demo"},
                "State": "running",
                "SizeRw": 10485760,
                "Ports": [{"PrivatePort": 80, "PublicPort": 8080, "Type": "tcp"}],
                "Mounts": [{"Type": "bind", "Destination": "/data", "Source": "/srv/data"}],
                "NetworkSettings": {"Networks": {"frontend": {}}},
                "HostConfig": {"NetworkMode": "frontend"},
            },
            {
                "Id": "zzz987yyy654",
                "Names": ["/db"],
                "Image": "postgres:16",
                "Labels": {},
                "State": "exited",
                "SizeRw": 2048,
                "Ports": [],
                "Mounts": [
                    {
                        "Type": "volume",
                        "Destination": "/var/lib/postgresql/data",
                        "Name": "pgdata",
                    }
                ],
                "NetworkSettings": {"Networks": {"backend": {}}},
                "HostConfig": {"NetworkMode": "backend"},
            },
        ]
        self.inspect_payloads = {
            "abc123def456": {
                "State": {
                    "Status": "running",
                    "StartedAt": started_at.isoformat().replace("+00:00", "Z"),
                    "Health": {"Status": "healthy"},
                }
            },
            "zzz987yyy654": {
                "State": {
                    "Status": "exited",
                    "StartedAt": started_at.isoformat().replace("+00:00", "Z"),
                }
            },
        }
        self.stats_payloads = {
            "abc123def456": {
                "cpu_stats": {
                    "cpu_usage": {"total_usage": 200000000, "percpu_usage": [1, 1]},
                    "system_cpu_usage": 2000000000,
                    "online_cpus": 2,
                },
                "precpu_stats": {
                    "cpu_usage": {"total_usage": 100000000},
                    "system_cpu_usage": 1000000000,
                },
                "memory_stats": {"usage": 134217728, "limit": 536870912},
                "networks": {"frontend": {"rx_bytes": 1024, "tx_bytes": 2048}},
            }
        }

    async def list_containers(self, include_size: bool = False) -> list[dict[str, Any]]:
        return self.containers

    async def inspect_container(self, container_id: str) -> dict[str, Any]:
        return self.inspect_payloads[container_id]

    async def container_stats(self, container_id: str) -> dict[str, Any]:
        return self.stats_payloads[container_id]


def test_service_builds_expected_rows() -> None:
    settings = load_settings(env={}, explicit_root=None)
    service = DockerDocumentationService(FakeDockerClient(), settings)

    overview_rows = asyncio.run(service.get_overview_rows())
    resource_rows = asyncio.run(service.get_resource_rows())
    port_rows = asyncio.run(service.get_port_rows())
    mount_rows = asyncio.run(service.get_mount_rows())

    assert [row.container_name for row in overview_rows] == ["db", "web"]
    assert overview_rows[1].stack == "demo"
    assert overview_rows[1].health_status == "Healthy"

    assert resource_rows[1].current_cpu_usage == "20.00%"
    assert resource_rows[1].current_memory_usage.startswith("128.0 MiB / 512.0 MiB")
    assert resource_rows[1].current_disk_usage == "10.0 MiB"

    assert len(port_rows) == 1
    assert port_rows[0].internal_port == "80/tcp"
    assert port_rows[0].external_port == "8080"

    assert len(mount_rows) == 2
    assert mount_rows[0].container_name == "db"
    assert mount_rows[1].external_path == "/srv/data"
