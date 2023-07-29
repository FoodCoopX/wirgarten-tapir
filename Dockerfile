FROM python:3.11
ARG TAPIR_VERSION
ENV TAPIR_VERSION=$TAPIR_VERSION
ENV PYTHONUNBUFFERED=1
COPY . /app
WORKDIR /app

RUN apt update -y && apt install -y libldap2-dev libsasl2-dev gettext

RUN echo "Building Tapir Version: $TAPIR_VERSION" && pip install poetry && poetry install
