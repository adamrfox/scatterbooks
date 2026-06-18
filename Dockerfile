# ---- Stage 1: build the React frontend ----
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# vite.config.ts outDir is "../backend/app/static" relative to /app/frontend,
# so this lands at /app/backend/app/static for stage 2 to pick up.
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim AS runtime
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /app/backend/app/static ./app/static

ENV DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
