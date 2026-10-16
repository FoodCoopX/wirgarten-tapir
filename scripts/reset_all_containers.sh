#!/bin/sh
#
# Completely wipes all local data (postgres, keycloak, mailman, mailpit,
# uploads, vite caches) by removing the named docker volumes, then brings the
# stack back up and regenerates a fresh test dataset.
#
# Usage: ./scripts/reset_local_environment.sh

set -e

ORG=${1:-BIOTOP}
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.mail.yml}"

echo "Stopping and removing containers and volumes..."
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans

echo "Starting the stack..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "Waiting for Keycloak to become ready..."
i=0
until curl -sf http://localhost:8080/realms/tapir >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 120 ]; then
        echo "Keycloak did not become ready in time." >&2
        exit 1
    fi
    sleep 2
done

echo "Applying migrations..."
docker compose -f "$COMPOSE_FILE" exec web poetry run python manage.py migrate

echo "Importing parameter definitions..."
docker compose -f "$COMPOSE_FILE" exec web poetry run python manage.py parameter_definitions

echo "Generating test data..."
docker compose -f "$COMPOSE_FILE" exec web poetry run python manage.py populate --reset_all "$ORG"
