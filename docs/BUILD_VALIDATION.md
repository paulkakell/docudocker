# Build validation

## Performed

- Created a fresh virtual environment.
- Installed runtime dependencies from `requirements.txt`.
- Executed `pip check`.
- Imported the FastAPI app successfully.
- Started the server with Uvicorn in the fresh environment and verified `/healthz`.

## Not performed

- Docker image build was not executed inside this sandbox because a Docker daemon was not available. The Dockerfile and compose assets are included for CI or host-side image build execution.
