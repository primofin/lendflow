# LendFlow API image. Build context: backend/
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /srv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
RUN useradd --system --uid 10001 --home-dir /srv app
WORKDIR /srv
COPY --from=build /srv/.venv .venv
COPY app app
COPY alembic alembic
COPY alembic.ini .
COPY scripts scripts
COPY docker/entrypoint.sh /entrypoint.sh
ENV PATH="/srv/.venv/bin:$PATH" PYTHONUNBUFFERED=1 STORAGE_DIR=/data/storage
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
# API_HOST defaults to "::" so the API is reachable over Fly's private IPv6 network; it is never
# exposed publicly. Docker's IPv4 bridge needs API_HOST=0.0.0.0 (docker-compose.prod.yml).
ENV API_HOST="::"
CMD ["sh", "-c", "exec fastapi run app/main.py --host $API_HOST --port 8000"]
