# Architecture

## High-level flow

```text
Web browser
  -> FastAPI application
     -> DockerDocumentationService
        -> DockerClient
           -> /var/run/docker.sock or docker-socket-proxy
```

## Design choices

1. The UI is server-rendered once and then uses JavaScript fetch calls for tab data.
2. Each tab loads fresh data only when opened or refreshed. There is no background polling.
3. Docker read operations are constrained with a small concurrency limit to reduce host impact.
4. FastAPI docs are disabled because the app is intended as an operational UI, not a public developer API.
5. There is no persistent database, queue, or cache. This removes schema, migration, and state management complexity.

## Request path

- `/` returns the Jinja template and static assets.
- `/api/*` routes call the service layer.
- The service layer transforms Docker JSON into table rows.
- The browser applies client-side sorting and filtering to the returned rows.
