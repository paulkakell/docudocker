# DocuDocker Web App

Version: `01.00.00`

DocuDocker Web App is a lightweight FastAPI application that provides live documentation for local Docker infrastructure through either the Docker Unix socket or a restricted docker-socket-proxy endpoint. The UI is a dark-theme single-page interface with tabbed views for Overview, Resources, Ports, and Mounts. Each table supports per-column filtering and client-side ascending or descending sorting.

## Scope implemented

- Containerized web application with minimal runtime dependencies.
- Dynamic tab-driven data refresh.
- Footer link to `https://github.com/paulkakell/docudock`.
- Footer version display sourced from the tracked `VERSION` file.
- Overview table with container name, stack, running state, health, image, release, and uptime.
- Resources table with CPU, memory, RX, TX, and disk usage.
- Ports table with one row per port.
- Mounts table with one row per mount.
- Optional HTTP Basic authentication.
- Structured logging, security headers, and health endpoint.

## Architecture

```text
Browser
  -> FastAPI routes and static assets
      -> DockerDocumentationService
          -> DockerClient
              -> Docker socket or docker-socket-proxy
```

The application intentionally avoids background polling. Data is fetched only when a tab is loaded or manually refreshed. That keeps host impact low and aligns with the requirement for dynamic updates on tab load.

## Runtime configuration

| Variable | Default | Purpose |
|---|---|---|
| `DOCUDOCKER_VERSION` | `VERSION` file | Runtime version override |
| `DOCUDOCKER_HOST` | `127.0.0.1` | Bind host for direct execution. Container images set this to `0.0.0.0`. |
| `DOCUDOCKER_PORT` | `8080` | Bind port |
| `DOCUDOCKER_DOCKER_MODE` | `socket` | `socket` or `http` |
| `DOCUDOCKER_DOCKER_SOCKET_PATH` | `/var/run/docker.sock` | Unix socket path |
| `DOCUDOCKER_DOCKER_BASE_URL` | `http://docker-socket-proxy:2375` | Proxy base URL in HTTP mode |
| `DOCUDOCKER_DOCKER_API_VERSION` | `v1.43` | Docker API version prefix |
| `DOCUDOCKER_DOCKER_TIMEOUT_SECONDS` | `5.0` | Docker request timeout |
| `DOCUDOCKER_MAX_CONCURRENCY` | `4` | Concurrent Docker inspect or stats calls |
| `DOCUDOCKER_BASIC_AUTH_USER` | unset | Optional basic auth username |
| `DOCUDOCKER_BASIC_AUTH_PASSWORD` | unset | Optional basic auth password |
| `DOCUDOCKER_GITHUB_URL` | `https://github.com/paulkakell/docudock` | Footer repository URL |
| `DOCUDOCKER_LOG_LEVEL` | `INFO` | Log verbosity |

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Direct Docker socket deployment

```bash
docker compose -f compose.example.yml up --build
```

### Proxy deployment

```bash
docker compose -f compose.proxy.example.yml up --build
```

## API surface

- `GET /` renders the web application.
- `GET /healthz` returns a readiness payload without contacting Docker.
- `GET /api/meta` returns version and connection mode metadata.
- `GET /api/overview` returns overview rows.
- `GET /api/resources` returns resource rows.
- `GET /api/ports` returns port rows.
- `GET /api/mounts` returns mount rows.

## Verification commands

```bash
pytest
ruff check .
mypy app
bandit -r app
pip-audit -r requirements.txt
python scripts/performance_check.py
```

## Operational notes

- The Docker client is read-only. No mutation endpoints are implemented.
- The app applies a strict Content Security Policy and disables FastAPI docs in the runtime service.
- When using a direct socket mount, the container may need host Docker group access. The proxy pattern is the preferred least-privilege deployment.
