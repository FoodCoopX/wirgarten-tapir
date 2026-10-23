FROM python:3.14
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update -y && apt-get install -y gettext locales nodejs && \
    apt-get clean && \
    npm install -g mjml@4.14.1

RUN sed -i -e '/de_DE.UTF-8/s/^# //g' -e '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock
RUN pip install poetry==2.5.1 && poetry install --extras bakery

COPY tapir /app/tapir
COPY manage.py /app/manage.py
COPY Makefile /app/Makefile
COPY dist* /app/dist
RUN poetry run python manage.py compilemessages

ARG TAPIR_VERSION
ENV TAPIR_VERSION=$TAPIR_VERSION
RUN echo "Building Tapir Version: $TAPIR_VERSION"
