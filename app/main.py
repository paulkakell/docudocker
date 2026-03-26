from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import RequestResponseEndpoint

from app.config import Settings, load_settings
from app.docker_client import DockerClient, DockerUnavailableError
from app.logging_utils import configure_logging, log_event
from app.service import DockerDocumentationService, DocumentationServiceProtocol

ROOT_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(ROOT_DIR / "templates"))
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _settings_from_request(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _service_from_request(request: Request) -> DocumentationServiceProtocol:
    return cast(DocumentationServiceProtocol, request.app.state.service)


def _is_authorized(header_value: str | None, settings: Settings) -> bool:
    if not settings.auth_enabled:
        return True
    if not header_value:
        return False
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "basic" or not token:
        return False
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    username, separator, password = decoded.partition(":")
    if not separator:
        return False
    return (
        username == (settings.basic_auth_user or "")
        and password == (settings.basic_auth_password or "")
    )


def create_app(
    settings: Settings | None = None,
    service: DocumentationServiceProtocol | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        app.state.settings = resolved_settings
        if service is not None:
            app.state.service = service
            yield
            return
        docker_client = DockerClient(resolved_settings)
        app.state.docker_client = docker_client
        app.state.service = DockerDocumentationService(docker_client, resolved_settings)
        yield
        await docker_client.aclose()

    app = FastAPI(
        title="DocuDocker Web App",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    if service is not None:
        app.state.service = service
    app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid4().hex[:12])
        request.state.request_id = request_id
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            log_event(
                40,
                "request.failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise
        response.headers["X-Request-ID"] = request_id
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        log_event(
            20,
            "request.completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    @app.middleware("http")
    async def authentication_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        current_settings = _settings_from_request(request)
        if request.url.path != "/healthz" and not _is_authorized(
            request.headers.get("Authorization"),
            current_settings,
        ):
            return JSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="DocuDocker"'},
                content={"detail": "Unauthorized"},
            )
        return await call_next(request)

    @app.middleware("http")
    async def security_headers_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if request.url.path.startswith("/static/"):
            response.headers.setdefault("Cache-Control", "public, max-age=3600")
        else:
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(DockerUnavailableError)
    async def docker_error_handler(request: Request, exc: DockerUnavailableError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        log_event(
            30,
            "docker.unavailable",
            request_id=request_id,
            path=request.url.path,
            detail=str(exc),
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Docker API unavailable",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        current_settings = _settings_from_request(request)
        context = {
            "request": request,
            "version": current_settings.version,
            "github_url": current_settings.github_url,
        }
        return TEMPLATES.TemplateResponse(request=request, name="index.html", context=context)

    @app.get("/healthz")
    async def healthz(request: Request) -> JSONResponse:
        current_settings = _settings_from_request(request)
        return JSONResponse(content={"status": "ok", "version": current_settings.version})

    @app.get("/api/meta")
    async def meta(request: Request) -> JSONResponse:
        current_settings = _settings_from_request(request)
        return JSONResponse(
            content={
                "version": current_settings.version,
                "github_url": current_settings.github_url,
                "docker_mode": current_settings.docker_mode,
            }
        )

    @app.get("/api/overview")
    async def overview(request: Request) -> JSONResponse:
        payload = await _service_from_request(request).overview_payload()
        return JSONResponse(content=payload)

    @app.get("/api/resources")
    async def resources(request: Request) -> JSONResponse:
        payload = await _service_from_request(request).resources_payload()
        return JSONResponse(content=payload)

    @app.get("/api/ports")
    async def ports(request: Request) -> JSONResponse:
        payload = await _service_from_request(request).ports_payload()
        return JSONResponse(content=payload)

    @app.get("/api/mounts")
    async def mounts(request: Request) -> JSONResponse:
        payload = await _service_from_request(request).mounts_payload()
        return JSONResponse(content=payload)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    runtime_settings = load_settings()
    uvicorn.run(
        "app.main:app",
        host=runtime_settings.host,
        port=runtime_settings.port,
        reload=False,
    )
