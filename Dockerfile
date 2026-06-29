# ---- Stage 1: build the SPA ----
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: python runtime ----
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/commit-watcher.db \
    FRONTEND_DIR=/app/frontend

COPY backend/pyproject.toml backend/
COPY backend/commit_watcher backend/commit_watcher
RUN pip install ./backend

# Built SPA served by the backend.
COPY --from=frontend /build/dist /app/frontend

VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"

CMD ["commit-watcher", "serve", "--host", "0.0.0.0", "--port", "8000"]
