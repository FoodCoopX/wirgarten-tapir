FROM python:3.11
ARG TAPIR_VERSION
ENV TAPIR_VERSION=$TAPIR_VERSION
ENV PYTHONUNBUFFERED=1
COPY . /app
WORKDIR /app

RUN apt update -y && apt install -y libldap2-dev libsasl2-dev gettext
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt update -y && apt install -y nodejs && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g mjml@4.14.1
RUN echo "Building Tapir Version: $TAPIR_VERSION" && pip install poetry && poetry lock && poetry install && poetry run python manage.py compilemessages
