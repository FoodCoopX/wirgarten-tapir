#!/bin/sh

docker compose down
docker compose up -d --remove-orphans
docker compose exec web poetry run python manage.py migrate
docker compose exec web poetry run python manage.py parameter_definitions
docker compose exec web poetry run python manage.py populate --reset_all