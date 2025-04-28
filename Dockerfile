FROM python:3.13
ARG TAPIR_VERSION
ENV TAPIR_VERSION=$TAPIR_VERSION
ENV PYTHONUNBUFFERED=1
COPY . /app
WORKDIR /app

RUN apt-get update -y && apt-get install -y libldap2-dev libsasl2-dev gettext locales
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update -y && apt install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g mjml@4.14.1

RUN sed -i '/de_DE.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

RUN echo "Building Tapir Version: $TAPIR_VERSION" && pip install poetry && poetry lock && poetry install && poetry run python manage.py compilemessages
