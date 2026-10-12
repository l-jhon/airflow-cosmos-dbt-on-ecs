FROM python:3.12-slim AS builder

ARG ENV=dev

ENV ENV=${ENV} \
    APP_DIR=/project \
    APP_ENV=${ENV} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/var/cache/pypoetry \
    PIP_NO_CACHE_DIR=1

WORKDIR ${APP_DIR}

COPY pyproject.toml ./

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}" && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi && \
    pip uninstall -y poetry && \
    rm -rf /root/.cache ${POETRY_CACHE_DIR}

FROM python:3.12-slim AS final

ARG ENV=dev

ENV ENV=${ENV} \
    APP_DIR=/project \
    APP_ENV=${ENV} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR ${APP_DIR}

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -d /home/appuser -m appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=appuser:appuser dbt_project.yml profiles.yml packages.yml ./
COPY --chown=appuser:appuser models/ ./models/
COPY --chown=appuser:appuser macros/ ./macros/
COPY --chown=appuser:appuser seeds/ ./seeds/
COPY --chown=appuser:appuser tests/ ./tests/

RUN find /usr/local/lib/python3.12 -type d -name "__pycache__" -exec rm -rf {} + && \
    find /usr/local/lib/python3.12 -type f -name "*.pyc" -delete && \
    chown -R appuser:appuser ${APP_DIR}

USER appuser
