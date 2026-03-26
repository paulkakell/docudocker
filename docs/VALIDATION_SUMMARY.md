# Validation summary

## Version and release

- Version: `01.00.00`
- Release tag: `v01.00.00`
- Issue reference: `DD-001`
- Commit hash: pending artifact import into source control

## Automated tests

- Command: `pytest`
- Result: `17 passed, 1 warning`
- Warning detail: dependency-origin `python_multipart` deprecation warning from Starlette import path. No application code failure.

## Static analysis and security checks

- `ruff check .`: passed
- `mypy app scripts`: passed
- `bandit -r app -q`: passed
- `pip check`: passed
- `pip-audit -r requirements.txt`: attempted but inconclusive because the sandbox could not resolve the upstream advisory service

## Build validation

- Fresh virtual environment install: passed
- Runtime import smoke test: passed
- Uvicorn startup and `/healthz` check: passed

## Performance check

Synthetic benchmark results from `scripts/performance_check.py`:

- `get_overview_rows`: mean `0.89 ms`
- `get_resource_rows`: mean `0.84 ms`
- `get_port_rows`: mean `0.18 ms`
- `get_mount_rows`: mean `0.07 ms`

## Database review

- No database is used. Migration review is not applicable.

## Raw logs

See `docs/verification/` for command outputs.
