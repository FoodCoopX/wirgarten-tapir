# AGENTS.md

Tapir — community supported agriculture (CSA) management. Django + DRF backend, Django templates + React islands (Vite)
frontend.

Source of this file: `.agents/rules/base-rules.md` (`AGENTS.md` is a symlink — edit the source).
Role profiles: `.agents/agents/`. Task recipes: `.agents/skills/`. See [.agents/README.md](.agents/README.md).

## Stack

- Backend: Python 3.14, Django 6, DRF, drf-spectacular; Celery + Beat, Redis; PostgreSQL 14
- Auth: Keycloak via `django-allauth` (socialaccount)
- Frontend: React 19, TypeScript, Vite, `django_vite`, react-bootstrap / Bootstrap 5
- Tooling: Poetry, pnpm, pytest + pytest-django + factory-boy (no frontend tests), Black / Prettier / DjHTML
- Optional: `ortools` via poetry extra `bakery` (baking-plan solver; 503 without it)
- Locale/formats: German (`de_DE`)

## Layout

```
tapir/            Django project + apps
src_frontend/     React/TS, one folder per Django page
scripts/          dev helpers
docker/keycloak/  image, realm import, themes
schema.yml        generated OpenAPI schema — never hand-edit
vite.config.ts    lists every JS entry point
```

### Apps (`tapir/*`)

| App                        | Responsibility                                                                                                                   |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `wirgarten/`               | **Legacy core domain**: `Member`, `Subscription`, `ProductType`, `GrowingPeriod`, `PickupLocation`; main views, middleware, mail |
| `core/`                    | `TapirModel` base model (nanoid id, `created_at`, `updated_at`), health status                                                   |
| `accounts/`                | `TapirUser`, Keycloak integration, sessions                                                                                      |
| `subscriptions/`           | Subscriptions, notice periods, cancellations, confirmations                                                                      |
| `products/`                | Product catalog and pricing                                                                                                      |
| `payments/`                | SEPA mandates, payment transactions, mandate references                                                                          |
| `deliveries/`              | Delivery schedules and cycles                                                                                                    |
| `pickup_locations/`        | Pickup points and routes                                                                                                         |
| `coop/`                    | Cooperative shares, roles, member numbers                                                                                        |
| `associations/`            | Association membership types and prices                                                                                          |
| `bestell_wizard/`          | Order wizard flow / cart                                                                                                         |
| `bakery/`                  | Breads, baking events, OR-Tools scheduling solver                                                                                |
| `waiting_list/`            | Signup queue                                                                                                                     |
| `solidarity_contribution/` | Income-based solidarity pricing                                                                                                  |
| `configuration/`           | `TapirParameter` settings / feature flags                                                                                        |
| `generic_exports/`         | CSV & PDF export engine                                                                                                          |
| `log/`                     | Audit trail (`TextLogEntry`, `UpdateModelLogEntry`)                                                                              |
| `utils/`                   | Shared helpers, caching, data import, `populate` command                                                                         |
| `filepond_*`               | FilePond upload storage                                                                                                          |
| `settings/`                | `base.py`, `deployment.py`, `site.py`; env from `.env.local`                                                                     |

App layout: `models.py`, `views/` or `views.py`, `serializers.py`, `services/`, `urls.py`, `tasks.py`, `tests/`,
`migrations/`, `management/commands/`.
Routing: [tapir/urls.py](tapir/urls.py) includes per-app `urls.py`; apps mix DRF `DefaultRouter` with plain `path()`.

### Frontend (`src_frontend/*`)

- One folder per Django page, plus shared `components/`, `hooks/`, `utils/`, `types/`.
- Each feature has a `*_entry.tsx` that `createRoot()`s into a DOM node from a Django template. Register the entry in
  `rollupOptions.input` in [vite.config.ts](vite.config.ts) and include it via `{% load django_vite %}` +
  `{% vite_asset "<folder>/<x>_entry.tsx" %}`.
- `src_frontend/api-client/` is generated from `schema.yml` — never hand-edit.
- Fetch through [src_frontend/hooks/useApi.ts](src_frontend/hooks/useApi.ts) (CSRF token + base path from `env.ts`).
  React hooks only, no Redux/Zustand, no path aliases.

## Commands

All tasks are `make` targets ([Makefile](Makefile)); they detect host vs. container, so Docker wrapping never belongs in
prose. `make help` lists all.

| Command                                  | Does                                                         |
|------------------------------------------|--------------------------------------------------------------|
| `make up` / `make reset`                 | start containers / full rebuild incl. test data              |
| `make test-fast`                         | whole suite, reusing the test DB — default choice            |
| `make test-app APP=subscriptions`        | tests of one app                                             |
| `make test`                              | CI: format check, collectstatic, coverage                    |
| `make lint`                              | Black                                                        |
| `make frontend-build`                    | type-check + build bundles                                   |
| `make schema`                            | regenerate `schema.yml` **and** TS client after a DRF change |
| `make populate` / `make populate-bakery` | fresh test data                                              |
| `make manage ARGS="migrate"`             | any other management command                                 |

**Never run `pytest` or `manage.py` directly on the host** — integration tests are not path-separated and fail without
containers; `manage.py` has no DB/Redis/Keycloak.

Services: `web` (8000), `vite` (5173), `keycloak` (8080), `db` (5432), `redis` (6379), `celery`, `celery-beat`.

## Conventions

- **Models** inherit `tapir.core.models.TapirModel` (nanoid IDs prevent cross-model ID mixups; `created_at`/
  `updated_at`). Keep model classes to their own fields; helper methods only if they reference just that object's
  fields.
- **Business logic in service classes** under `tapir/<app>/services/`, not in views or models.
- **`cache` parameter**: a plain `dict` passed through service functions as a per-request query cache. Create it at the
  origin (view `__init__`, first lines of a command) and pass it down. Request-scoped, so usually no invalidation; if
  needed see `tapir.utils.services.tapir_cache_manager.TapirCacheManager`. Optional only for legacy callers — **make it
  required in new code**. Examples: usages of `tapir.utils.services.tapir_cache.TapirCache`.
- **`tapir/wirgarten/` is legacy** and ignores these conventions. When changing something there, consider rewriting the
  affected part into another app.
- **Tests** live in `tapir/<app>/tests/` (only `wirgarten` splits `unit/` / `integration/`), with `factories.py`
  (factory-boy). Integration tests subclass `TapirIntegrationTest`
  from [tapir/wirgarten/tests/test_utils.py](tapir/wirgarten/tests/test_utils.py), which mocks Keycloak in `setUp`;
  `setUpTestData` runs earlier, so **users cannot be created in `setUpTestData`**. Run via `make test-fast` /
  `make test-app APP=<app>`.
- **Annotate API views** with `@extend_schema(...)` and run `make schema`.
- **Formatting**: Black / Prettier / DjHTML, enforced by pre-commit (`poetry run pre-commit install`).
- **Commits**: [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/), referencing the GitHub issue ID
  when applicable.
- **Pull requests**: Pull request names should also follow conventional commits: they will be squashed and the PR's
  title will be used as commit message.