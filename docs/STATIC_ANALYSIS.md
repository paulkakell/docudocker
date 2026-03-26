# Static analysis and linting

Commands executed:

- `ruff check .`
- `mypy app scripts`
- `bandit -r app -q`

Results:

- Ruff: passed.
- Mypy: passed.
- Bandit: passed after removing the broad bind default from application configuration and relying on explicit container runtime configuration where needed.

Detailed command outputs are stored in `docs/verification/`.
