FROM node:24-trixie-slim AS mjml
RUN npm install -g mjml@4.14.1

FROM python:3.14.10 AS python-base
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_PATH=/opt/venvs

WORKDIR /app

RUN python -m venv /opt/poetry && \
    /opt/poetry/bin/pip install --no-cache-dir poetry==2.5.1 && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

COPY --from=mjml /usr/local/bin/node /usr/local/bin/node
COPY --from=mjml /usr/local/lib/node_modules/mjml /usr/local/lib/node_modules/mjml
RUN ln -s ../lib/node_modules/mjml/bin/mjml /usr/local/bin/mjml

RUN apt-get update -y && apt-get install -y --no-install-recommends locales && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i -e '/de_DE.UTF-8/s/^# //g' -e '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock

FROM python-base AS dev
RUN poetry install --extras bakery && rm -rf /root/.cache

FROM python-base AS builder
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
RUN poetry install --extras bakery --only main && rm -rf /root/.cache

COPY tapir /app/tapir
COPY manage.py /app/manage.py
COPY Makefile /app/Makefile
COPY dist* /app/dist

FROM python:3.14.10-slim AS prod
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH=/app/.venv/bin:$PATH

WORKDIR /app

# locales for the CSV export locales, pango/harfbuzz/fonts for weasyprint
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    locales libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i -e '/de_DE.UTF-8/s/^# //g' -e '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

COPY --from=mjml /usr/local/bin/node /usr/local/bin/node
COPY --from=mjml /usr/local/lib/node_modules/mjml /usr/local/lib/node_modules/mjml
RUN ln -s ../lib/node_modules/mjml/bin/mjml /usr/local/bin/mjml

COPY --from=builder /opt/poetry /opt/poetry
RUN ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry
COPY --from=builder /app /app

ARG TAPIR_VERSION
ENV TAPIR_VERSION=$TAPIR_VERSION
RUN echo "Building Tapir Version: $TAPIR_VERSION"
