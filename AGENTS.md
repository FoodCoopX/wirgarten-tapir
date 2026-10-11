# AGENTS.md

Tapir — management system for community supported agriculture (CSA).
Backend: Python / Django + DRF. Frontend: Django templates + React islands bundled by Vite.

See [README.md](README.md) for setup, contribution and domain background. This file is the map of the repo for coding agents.

## Documentation map

Short, always-applicable rules live in [.github/instructions/](.github/instructions/) and are loaded automatically for
matching files (`backend`, `frontend`, `tests`). Deeper context — read the relevant file before non-trivial work:

| Topic | Read |
|---|---|
| Overview, mental model, how to add a feature | [doc/dev/README.md](doc/dev/README.md) |
| Backend layering, services, `cache` contract, Keycloak permissions, Celery, `TapirParameter` | [doc/dev/architecture.md](doc/dev/architecture.md) |
| Django↔React bridge, entry points, generated API client | [doc/dev/frontend.md](doc/dev/frontend.md) |
| Entities, date-ranged data, money, migrations | [doc/dev/domain-model.md](doc/dev/domain-model.md) |
| Test base classes, Keycloak mock, factories | [doc/dev/testing.md](doc/dev/testing.md) |
| Settings, env vars, services, deployment checklist | [doc/dev/operations.md](doc/dev/operations.md) |
| Security-sensitive regions and invariants | [doc/dev/security.md](doc/dev/security.md) |

German admin/operator documentation: [doc/README.md](doc/README.md).

## Tech stack

| Area | Tech |
|---|---|
| Backend | Python 3.14, Django 6, Django REST Framework, drf-spectacular |
| Async | Celery + Celery Beat, Redis |
| DB | PostgreSQL 14 |
| Auth | Keycloak via `django-allauth` (socialaccount) |
| Frontend | React 19 + TypeScript, Vite, `django_vite`, react-bootstrap / Bootstrap 5 |
| Package mgmt | Poetry (Python), pnpm (JS) |
| Tests | pytest + pytest-django + factory-boy (no frontend tests) |
| Formatting | Black (py), Prettier (ts/tsx), DjHTML (templates) |
| Optional | `ortools` via the `bakery` poetry extra (baking-plan solver, else 503) |

## Repo layout

```
tapir/              Django project + apps (backend)
src_frontend/       React/TypeScript sources, one folder per feature
scripts/            dev helper scripts (reset, schema + client generation)
docker/keycloak/    Keycloak image, realm import, themes
schema.yml          generated OpenAPI schema (do not hand-edit)
vite.config.ts      lists every JS entry point
```

### Django apps (`tapir/*`)

| App | Responsibility |
|---|---|
| `wirgarten/` | **Legacy core domain**: `Member`, `Subscription`, `ProductType`, `GrowingPeriod`, `PickupLocation`; main views, middleware, mail |
| `core/` | `TapirModel` base model (nanoid id, `created_at`, `updated_at`), health status |
| `accounts/` | `TapirUser`, Keycloak integration, sessions |
| `subscriptions/` | Subscriptions, notice periods, cancellations, confirmations |
| `products/` | Product catalog and pricing |
| `payments/` | SEPA mandates, payment transactions, mandate references |
| `deliveries/` | Delivery schedules and cycles |
| `pickup_locations/` | Pickup points and routes |
| `coop/` | Cooperative shares, roles, member numbers |
| `associations/` | Association membership types and prices |
| `bestell_wizard/` | Order wizard flow / cart |
| `bakery/` | Breads, baking events, OR-Tools scheduling solver |
| `waiting_list/` | Signup queue |
| `solidarity_contribution/` | Income-based solidarity pricing |
| `configuration/` | `TapirParameter` system settings / feature flags |
| `generic_exports/` | CSV & PDF export engine |
| `log/` | Audit trail (`TextLogEntry`, `UpdateModelLogEntry`) |
| `utils/` | Shared helpers, caching, data import, `populate` command |
| `filepond_*` | FilePond upload storage |
| `settings/` | `base.py`, `deployment.py`, `site.py`; env read from `.env.local` |

Typical app layout: `models.py`, `views/` or `views.py`, `serializers.py`, `services/`, `urls.py`, `tasks.py`, `tests/`, `migrations/`, `management/commands/`.

Routing: [tapir/urls.py](tapir/urls.py) includes per-app `urls.py`; apps mix DRF `DefaultRouter` registrations with plain `path()` views.

### Frontend (`src_frontend/*`)

- One folder per feature (`member_profile/`, `dashboard/`, `bestell_wizard_mobile/`, `member_list/`, `product_config/`, …), plus shared `components/`, `hooks/`, `utils/`, `types/`.
- Each feature exposes a `*_entry.tsx` that `createRoot()`s into a DOM node rendered by a Django template. Entries must be registered in `rollupOptions.input` in [vite.config.ts](vite.config.ts) and included in the template via `{% load django_vite %}` + `{% vite_asset "<folder>/<x>_entry.tsx" %}`.
- `src_frontend/api-client/` is **generated** from `schema.yml` — never hand-edit.
- Data fetching goes through [src_frontend/hooks/useApi.ts](src_frontend/hooks/useApi.ts) (injects CSRF token and base path from `env.ts`). No Redux/Zustand — React hooks only. No path aliases.

## Common commands

```bash
# Full local reset (docker)
./scripts/reset_all_containers.sh

# Tests
docker compose exec web poetry run pytest --reuse-db -n auto   # all
poetry run pytest                                              # unit tests, outside docker
make test                                                      # black check + collectstatic + pytest w/ coverage

# Formatting / lint
make lint                 # black .
pnpm lint                 # eslint
poetry run pre-commit install

# API schema + TS clients (run after changing a DRF view)
docker compose exec web ./scripts/generate_api_schema.sh \
  && docker compose exec vite ./scripts/generate_api_clients.sh

# Useful management commands
python manage.py populate --reset_all [--org=bakery]
python manage.py parameter_definitions
python manage.py spectacular --file schema.yml
```

Docker services: `web` (8000), `vite` (5173), `keycloak` (8080), `db` (5432), `redis` (6379), `celery`, `celery-beat`.

## Conventions

- **Models** inherit `tapir.core.models.TapirModel` (nanoid IDs). Keep models to their own fields; helper methods only if they reference only that object's fields.
- **Business logic lives in service classes** under `tapir/<app>/services/`, not in views or models.
- **`cache` parameter**: many service functions take a plain `dict` used as a per-request cache to avoid redundant DB queries. Create it at the origin (view `__init__`, start of a command) and pass it down; prefer making it required in new code. See `tapir.utils.services.tapir_cache.TapirCache` and `tapir_cache_manager.TapirCacheManager` for invalidation.
- **`tapir/wirgarten/` is legacy** and does not follow these conventions. When touching it, rewrite the affected part into one of the other apps if feasible.
- **Tests**: per-app `tapir/<app>/tests/` (often split `unit/` / `integration/`), `factories.py` with factory-boy. Integration tests subclass `TapirIntegrationTest` from [tapir/wirgarten/tests/test_utils.py](tapir/wirgarten/tests/test_utils.py), which mocks Keycloak in `setUp` — so **users cannot be created in `setUpTestData`**. Integration tests must run inside Docker.
- **Commits**: [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/), referencing the GitHub issue ID when applicable.
- **Annotate API views** with `@extend_schema(...)` so the generated schema and TS clients stay useful.
- Default locale/formats are German (`de_DE`).
