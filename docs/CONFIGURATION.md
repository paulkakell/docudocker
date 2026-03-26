# Configuration validation

The runtime validates the following conditions on startup:

- Port must be within `1..65535`.
- Docker mode must be `socket` or `http`.
- HTTP mode requires an absolute proxy URL.
- Docker timeout must be greater than zero.
- Concurrency must be at least one.
- Basic auth username and password must be provided together or omitted together.

## Deployment modes

### Socket mode

Use when the app is colocated with the Docker daemon and a direct Unix socket mount is acceptable.

### HTTP mode

Use with a restricted docker-socket-proxy container. This is the preferred deployment because it narrows the exposed Docker API surface.
