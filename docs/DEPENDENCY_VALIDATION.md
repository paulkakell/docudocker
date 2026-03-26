# Dependency validation

## Runtime dependencies

- `fastapi==0.111.0`
- `httpx==0.28.1`
- `jinja2==3.1.6`
- `uvicorn==0.40.0`

## Validation performed

- Dependencies pinned in `requirements.txt`.
- Fresh environment install performed with `pip install -r requirements.txt`.
- Compatibility check executed with `pip check`.
- Vulnerability audit attempted with `pip-audit -r requirements.txt`.

## Result

- Compatibility: passed.
- Fresh install: passed.
- Vulnerability audit: inconclusive in this sandbox because `pip-audit` could not reach the upstream advisory endpoint. The command output is preserved in `docs/verification/pip-audit.log`.

## Notes

The runtime dependency set was kept deliberately small to reduce attack surface and improve container startup time.
