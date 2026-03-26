from datetime import UTC, datetime

from app.formatters import (
    cpu_percent,
    derive_stack,
    format_uptime,
    humanize_bytes,
    network_names,
    parse_release,
)


def test_parse_release_prefers_tag() -> None:
    assert parse_release("ghcr.io/example/web:1.2.3") == "1.2.3"
    assert parse_release("ghcr.io/example/web") == "latest"


def test_humanize_bytes_scales_values() -> None:
    assert humanize_bytes(0) == "0 B"
    assert humanize_bytes(1024) == "1.0 KiB"
    assert humanize_bytes(1048576) == "1.0 MiB"


def test_format_uptime_for_running_container() -> None:
    now = datetime(2026, 3, 26, 12, 0, tzinfo=UTC)
    uptime_text, uptime_sort = format_uptime("2026-03-26T11:30:00Z", True, now)
    assert uptime_text == "30m"
    assert uptime_sort == 1800


def test_derive_stack_falls_back_to_standalone() -> None:
    assert derive_stack({"com.docker.compose.project": "demo"}) == "demo"
    assert derive_stack({}) == "Standalone"


def test_network_names_collects_sorted_values() -> None:
    container = {
        "NetworkSettings": {"Networks": {"backend": {}, "frontend": {}}},
        "HostConfig": {"NetworkMode": "bridge"},
    }
    assert network_names(container) == "backend, frontend"


def test_cpu_percent_uses_docker_stats_formula() -> None:
    stats = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 200, "percpu_usage": [1, 1]},
            "system_cpu_usage": 2000,
            "online_cpus": 2,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 100},
            "system_cpu_usage": 1000,
        },
    }
    assert cpu_percent(stats) == 20.0
