# Logging and observability

## Logging

The app emits structured JSON logs with the following keys:

- `timestamp`
- `level`
- `event`
- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

## Health

`GET /healthz` returns a lightweight readiness response without contacting Docker. This allows container orchestrators to probe liveness even if the Docker daemon is temporarily slow or unavailable.

## Metrics and alerts

No metrics backend is included in this artifact. Operational alerting can be layered by scraping structured logs or by fronting the service with a reverse proxy that exports request metrics.
