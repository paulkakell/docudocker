# Changelog

## 01.00.00 - 2026-03-26

Release tag: `v01.00.00`
Issue reference: `DD-001`
Commit hash: pending artifact import into source control
Release classification: additive initial release

### Changed
- Added a FastAPI-based dark theme web interface with Overview, Resources, Ports, and Mounts tabs.
- Added Docker data collection over either the local Unix socket or an HTTP docker-socket-proxy target.
- Added client-side sorting and per-column unique-value filtering for every table.
- Added structured JSON logging, optional HTTP Basic authentication, health checks, and response hardening headers.
- Added container build assets, local compose examples, and operational documentation.

### Why
- The uploaded requirements call for a lightweight, dynamic, containerized interface that documents local Docker infrastructure with minimal host impact.

### Compatibility
- Breaking: no.
- Additive: yes.
- Fix: no.
