# Performance check

The application avoids continuous polling and only requests Docker data when a tab is opened or refreshed. Concurrency for inspect or stats calls is capped by configuration to reduce daemon pressure.

A synthetic service benchmark is included in `scripts/performance_check.py`. The benchmark exercises the transformation layer with a 40-container synthetic dataset across overview, resources, ports, and mounts operations.
