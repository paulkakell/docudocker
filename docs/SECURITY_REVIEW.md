# Security review

## Summary

The application is read-only and limited to GET routes. It does not write to Docker, local storage, or a database. The primary security concern is protecting access to Docker metadata and limiting exposure when connecting to the Docker daemon.

## Controls implemented

- Optional HTTP Basic authentication for all routes except `/healthz`.
- Strict Content Security Policy limited to self-hosted assets.
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: no-referrer`.
- FastAPI docs disabled to reduce attack surface.
- Docker client performs only read calls.
- Logs avoid credentials and request payload echoing.
- Proxy deployment example restricts Docker socket proxy permissions.

## OWASP-oriented review

- Broken access control: mitigated with optional basic auth and a recommended reverse proxy or network boundary.
- Cryptographic failures: no sensitive at-rest storage; recommend TLS termination in front of the app.
- Injection: no SQL, shell, or template injection paths. Templates do not render user-controlled HTML.
- Insecure design: no mutation actions and minimal exposed API surface.
- Security misconfiguration: headers added, docs disabled, auth validated, and proxy mode documented.
- Vulnerable components: dependency audit attempted with `pip-audit`, but advisory lookup was blocked by sandbox network resolution.
- Identification and authentication failures: basic auth supported, but production deployments should prefer a stronger front-end identity layer when available.
- Software and data integrity failures: versioned artifacts, requirements pinning, and change log included.
- Security logging and monitoring failures: structured JSON request logs and health endpoint included.
- Server-side request forgery: outbound calls are limited to a configured Docker socket or explicit proxy target, not arbitrary user input.

## Residual risks

- Direct Docker socket access remains privileged. The docker-socket-proxy pattern is safer and preferred.
- Basic auth is intentionally simple. Production deployments should add TLS and, where possible, external authentication.
- Dependency vulnerability status is partially validated only. Compatibility passed, but upstream advisory lookup was unavailable inside this sandbox.
