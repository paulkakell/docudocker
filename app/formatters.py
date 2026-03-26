from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

JsonMapping = Mapping[str, Any]


def normalize_container_name(names: Sequence[str] | None, fallback: str) -> str:
    if not names:
        return fallback[:12]
    return names[0].lstrip("/") or fallback[:12]


def derive_stack(labels: Mapping[str, str] | None) -> str:
    if not labels:
        return "Standalone"
    for key in (
        "com.docker.compose.project",
        "com.docker.stack.namespace",
        "io.portainer.stack.name",
    ):
        value = labels.get(key)
        if value:
            return value
    return "Standalone"


def parse_release(image: str) -> str:
    if not image:
        return "-"
    digest_delimiter_index = image.rfind("@")
    if digest_delimiter_index != -1:
        digest = image[digest_delimiter_index + 1 :]
        if digest.startswith("sha256:"):
            return digest[:19]
        return digest or "-"
    slash_delimiter_index = image.rfind("/")
    colon_delimiter_index = image.rfind(":")
    if colon_delimiter_index > slash_delimiter_index:
        return image[colon_delimiter_index + 1 :] or "latest"
    return "latest"


def title_case_status(value: str | None, fallback: str = "Unknown") -> str:
    if not value:
        return fallback
    return value.replace("_", " ").title()


def humanize_bytes(value: int | float | None) -> str:
    if value is None or value <= 0:
        return "0 B"
    size = float(value)
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return "0 B"


def _parse_timestamp(timestamp: str | None) -> datetime | None:
    if not timestamp or timestamp.startswith("0001-01-01"):
        return None
    normalized = timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def humanize_duration(total_seconds: int) -> str:
    if total_seconds <= 0:
        return "0s"
    remaining = total_seconds
    parts: list[str] = []
    for unit, scale in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if remaining >= scale or (unit == "s" and not parts):
            amount, remaining = divmod(remaining, scale)
            if amount > 0 or unit == "s":
                parts.append(f"{amount}{unit}")
        if len(parts) == 3:
            break
    return " ".join(parts)


def format_uptime(
    started_at: str | None,
    is_running: bool,
    now: datetime | None = None,
) -> tuple[str, int]:
    if not is_running:
        return "-", 0
    started = _parse_timestamp(started_at)
    if started is None:
        return "-", 0
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    seconds = max(int((current - started).total_seconds()), 0)
    return humanize_duration(seconds), seconds


def cpu_percent(stats: JsonMapping) -> float:
    cpu_stats = stats.get("cpu_stats")
    precpu_stats = stats.get("precpu_stats")
    if not isinstance(cpu_stats, Mapping) or not isinstance(precpu_stats, Mapping):
        return 0.0

    current_cpu_usage = cpu_stats.get("cpu_usage")
    previous_cpu_usage = precpu_stats.get("cpu_usage")
    if not isinstance(current_cpu_usage, Mapping) or not isinstance(previous_cpu_usage, Mapping):
        return 0.0

    total_usage = int(current_cpu_usage.get("total_usage", 0) or 0)
    previous_total_usage = int(previous_cpu_usage.get("total_usage", 0) or 0)
    system_usage = int(cpu_stats.get("system_cpu_usage", 0) or 0)
    previous_system_usage = int(precpu_stats.get("system_cpu_usage", 0) or 0)
    cpu_delta = total_usage - previous_total_usage
    system_delta = system_usage - previous_system_usage
    if cpu_delta <= 0 or system_delta <= 0:
        return 0.0

    online_cpus = int(cpu_stats.get("online_cpus", 0) or 0)
    if online_cpus <= 0:
        per_cpu_usage = current_cpu_usage.get("percpu_usage")
        online_cpus = (
            len(per_cpu_usage) if isinstance(per_cpu_usage, list) and per_cpu_usage else 1
        )

    return round((cpu_delta / system_delta) * online_cpus * 100, 2)


def memory_usage(stats: JsonMapping) -> tuple[str, int]:
    memory_stats = stats.get("memory_stats")
    if not isinstance(memory_stats, Mapping):
        return "0 B", 0
    usage = int(memory_stats.get("usage", 0) or 0)
    limit = int(memory_stats.get("limit", 0) or 0)
    if usage <= 0:
        return "0 B", 0
    if limit > 0:
        percent = round((usage / limit) * 100, 1)
        return f"{humanize_bytes(usage)} / {humanize_bytes(limit)} ({percent}%)", usage
    return humanize_bytes(usage), usage


def network_usage(stats: JsonMapping) -> tuple[str, int, str, int]:
    networks = stats.get("networks")
    if not isinstance(networks, Mapping):
        return "0 B", 0, "0 B", 0
    rx_total = 0
    tx_total = 0
    for details in networks.values():
        if isinstance(details, Mapping):
            rx_total += int(details.get("rx_bytes", 0) or 0)
            tx_total += int(details.get("tx_bytes", 0) or 0)
    return humanize_bytes(rx_total), rx_total, humanize_bytes(tx_total), tx_total


def network_names(container: JsonMapping) -> str:
    network_settings = container.get("NetworkSettings")
    if isinstance(network_settings, Mapping):
        networks = network_settings.get("Networks")
        if isinstance(networks, Mapping) and networks:
            return ", ".join(sorted(str(name) for name in networks))
    host_config = container.get("HostConfig")
    if isinstance(host_config, Mapping):
        network_mode = host_config.get("NetworkMode")
        if isinstance(network_mode, str) and network_mode:
            return network_mode
    return "-"


def health_status(state: JsonMapping | None) -> str:
    if not isinstance(state, Mapping):
        return "N/A"
    health = state.get("Health")
    if isinstance(health, Mapping):
        health_value = health.get("Status")
        if isinstance(health_value, str) and health_value:
            return title_case_status(health_value)
    return "N/A"
