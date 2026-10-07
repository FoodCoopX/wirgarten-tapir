#!/bin/sh

set -e
poetry lock
poetry install
docker compose down
docker compose up -d --remove-orphans keycloak db redis
poetry run python manage.py migrate
poetry run python manage.py parameter_definitions
poetry run python manage.py populate --reset_all
poetry run python manage.py runserver_plus 0.0.0.0:8000 --reloader-type=stat