FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

FROM base AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM builder AS dev-builder
RUN uv sync --frozen

FROM base AS app-base
ARG USER=app
ARG APP_UID=10001
ARG APP_GID=10001
RUN groupadd --gid ${APP_GID} ${USER} && \
    useradd --uid ${APP_UID} --gid ${APP_GID} --no-create-home \
    --shell /usr/sbin/nologin ${USER}

WORKDIR /app
COPY --from=builder --chown=${USER}:${USER} /app/.venv /app/.venv
COPY --chown=${USER}:${USER} . /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER ${USER}
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM app-base AS development
COPY --from=dev-builder --chown=${USER}:${USER} /app/.venv /app/.venv

FROM app-base AS runtime
