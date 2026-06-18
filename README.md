# scatterbooks
A simple book tracking web app

## Running it

```sh
docker build -t scatterbooks .
docker run -d --name scatterbooks \
  -e INITIAL_ADMIN_USERNAME=admin -e INITIAL_ADMIN_PASSWORD=<choose-a-password> \
  -v scatterbooks_data:/data -p 8000:8000 scatterbooks
```

See [docs/deployment.md](docs/deployment.md) for environment variables, data
persistence, and the nginx reverse-proxy setup for production.

## Backend development

This host has no system Python pip/venv, so backend commands run inside a `python:3.12-slim`
container with the `backend/` dir bind-mounted. From `backend/`:

```sh
# run tests
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$(pwd)":/app -w /app python:3.12-slim \
  sh -c "pip install -q -r requirements.txt --user && PATH=/tmp/.local/bin:\$PATH python -m pytest -v"

# run a dev server on http://localhost:8123 (data persisted in /tmp/scatterbooks-dev-data)
mkdir -p /tmp/scatterbooks-dev-data
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e DATA_DIR=/data \
  -e INITIAL_ADMIN_USERNAME=admin -e INITIAL_ADMIN_PASSWORD=adminpass123 \
  -v "$(pwd)":/app -v /tmp/scatterbooks-dev-data:/data -w /app -p 127.0.0.1:8123:8000 \
  python:3.12-slim sh -c "pip install -q -r requirements.txt --user && PATH=/tmp/.local/bin:\$PATH \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

Migrations and the initial admin bootstrap run automatically on app startup (see `app/main.py`).

## Frontend development

No system Node either, so frontend commands run inside a `node:22-slim` container with the
`frontend/` dir bind-mounted. From the repo root:

```sh
# install deps / add a package
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$(pwd)":/app -w /app/frontend node:22-slim \
  sh -c "npm install"

# dev server with hot reload on http://localhost:5173 (proxies /api to localhost:8000 --
# run the backend dev server above first); add -p 5173:5173 to the docker run if testing
# from outside the container
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$(pwd)":/app -w /app/frontend \
  -p 5173:5173 node:22-slim sh -c "npm run dev -- --host"

# lint + typecheck + production build (outputs straight into backend/app/static,
# which FastAPI serves as the SPA -- see the catch-all route in backend/app/main.py)
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$(pwd)":/app -w /app/frontend node:22-slim \
  sh -c "npm run lint && npm run build"
```

After `npm run build`, run the backend dev server (above) and open `http://localhost:8123/` to
exercise the built SPA end-to-end through the real FastAPI app, the same way it'll run in
production behind the external nginx.
