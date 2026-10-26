# Tapir task runner.
#
# Anything that touches Django, the database or pytest has to run inside the
# `web` container: the integration tests need the containers for Postgres and
# Redis, and manage.py has nothing to talk to on the host.
#
# You do not have to think about that wrapper. On the host these targets are
# sent to the running container; inside a container (CI runs
# `docker compose run web make test`) they execute directly.

ifeq (,$(wildcard /.dockerenv))
  IN_WEB := docker compose exec web
  IN_VITE := docker compose exec vite
else
  IN_WEB :=
  IN_VITE :=
endif

APP ?=
ARGS ?=

.DEFAULT_GOAL := help

.PHONY: help up down reset lint test-lint test test-fast test-app \
	manage migrate parameters populate populate-bakery keycloak schema frontend-build \
	publish-docker-image

help: ## Show this help
	@grep -hE '^[a-z][a-z-]*:.*## ' $(MAKEFILE_LIST) \
		| sort \
		| awk -F':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## --- Containers -----------------------------------------------------------

up: ## Start all containers in the background
	docker compose up -d

down: ## Stop all containers
	docker compose down

reset: ## Full rebuild: containers, migrations, parameters and test data
	./scripts/reset_all_containers.sh

## --- Tests ----------------------------------------------------------------

test-fast: ## Whole suite, no coverage, reusing the test database
	$(IN_WEB) poetry run pytest --reuse-db -n auto

test-app: ## Tests of one app, e.g. make test-app APP=subscriptions
	@test -n "$(APP)" || { echo 'usage: make test-app APP=<django app>'; exit 1; }
	$(IN_WEB) poetry run pytest tapir/$(APP)/tests --reuse-db

test: test-lint ## Full run as CI does it: format check, collectstatic, coverage
	find tapir -path "*/tests/*.py" | grep -q . || exit 0; \
	$(IN_WEB) poetry run python manage.py collectstatic --noinput
	$(IN_WEB) poetry run pytest --cov-report xml:coverage.xml --cov=tapir --cov-config=pyproject.toml -n auto

## --- Formatting -----------------------------------------------------------

lint: ## Format Python files with Black
	$(IN_WEB) poetry run black .

test-lint: ## Check Python formatting without writing
	$(IN_WEB) poetry run black --check .

frontend-build: ## Type-check and build the frontend bundles
	$(IN_VITE) pnpm build

## --- Django ---------------------------------------------------------------

manage: ## Any management command, e.g. make manage ARGS="createsuperuser"
	@test -n "$(ARGS)" || { echo 'usage: make manage ARGS="<command> [options]"'; exit 1; }
	$(IN_WEB) poetry run python manage.py $(ARGS)

migrate: ## Apply database migrations
	$(IN_WEB) poetry run python manage.py migrate

parameters: ## Import the TapirParameter definitions
	$(IN_WEB) poetry run python manage.py parameter_definitions

populate: ## Drop the data and generate a fresh test dataset
	$(IN_WEB) poetry run python manage.py populate --reset_all

keycloak: ## Keycloak users on the command line, e.g. make keycloak ARGS="user list"
	@test -n "$(ARGS)" || { ./scripts/tapir_kcadm.sh --help; exit 1; }
	./scripts/tapir_kcadm.sh $(ARGS)

populate-bakery: ## Same as populate, with the bakery organisation switched on
	$(IN_WEB) poetry run python manage.py populate --reset_all --org=bakery

## --- Generated artifacts --------------------------------------------------

schema: ## Regenerate schema.yml and the TypeScript API client
	$(IN_WEB) ./scripts/generate_api_schema.sh
	$(IN_VITE) ./scripts/generate_api_clients.sh

## --- Release --------------------------------------------------------------

publish-docker-image:
	gh workflow -R foodcoopx/wirgarten-tapir run "Create and publish Docker image"
