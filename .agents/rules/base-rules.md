# AGENTS.md

Tapir — community supported agriculture (CSA) management. Django + DRF backend, Django templates + React islands (Vite)
frontend.

Source of this file: `.agents/rules/base-rules.md` (`AGENTS.md` is a symlink — edit the source).
Role profiles: `.agents/agents/`. Task recipes: `.agents/skills/`. See [.agents/README.md](.agents/README.md).

## Stack

- Backend: Python 3.14, Django 6, DRF, drf-spectacular; Celery + Beat, Redis; PostgreSQL 18
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
- Date-only API fields (`format: date`) are `"YYYY-MM-DD"` strings in the generated client; date-time fields stay `Date`.
  Never pass them to `new Date(...)` (parses as UTC): use `fromApiDate` / `toApiDate` from
  [src_frontend/utils/apiDate.ts](src_frontend/utils/apiDate.ts). Compare and sort them as strings. Pass them to `formatDate…` as strings
  (`toApiDate(date)` if you only have a `Date`). Details in [docs/dev/frontend_dates.md](docs/dev/frontend_dates.md).
- Fetch through [src_frontend/hooks/useApi.ts](src_frontend/hooks/useApi.ts) (CSRF token + base path from `env.ts`).
  React hooks only, no Redux/Zustand, no path aliases.
- Button variants by what the button does:
    - `outline-secondary`: no effect (close a modal, cancel, go back, navigate to another page).
    - `outline-primary`: no effect yet, but leads to a button that has one (open a form, go to a confirmation step).
    - `primary`: does something permanent (save, send a mail).
    - `danger` / `outline-danger`: only for deletions, instead of `primary` / `outline-primary` with the same
      rules (`outline-danger` opens the delete confirmation, `danger` deletes).

## Commands

All tasks are `make` targets ([Makefile](Makefile)); on the host they always run inside the `web` container (see
**Host vs. Docker** below). `make help` lists all.

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

**Host vs. Docker**: check whether `.env.local` exists in the repository root.

- Exists (local setup): run directly on the host, e.g. `poetry run pytest --reuse-db`,
  `poetry run python manage.py <cmd>`.
- Missing (Docker setup): use the `make` targets above, or `docker compose exec -T web poetry run pytest --reuse-db`.
  Running `pytest` or `manage.py` on the host fails here (host `db` does not resolve).

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
- **Test naming**: one file per tested class/function, `test_<snake_case_name>.py`, class `Test<ClassOrFunctionName>`.
  **Only one test class per file**: never add a second class to an existing file. To split a service's tests by method,
  use a directory named after the service with one file per method
  (e.g. `tests/services/member_pickup_location_cleaner/test_should_clean_pickup_location.py`).
  Methods follow `test_<method>_<condition>_<expectedResult>`, each part in camelCase, e.g.
  `test_validateInstalments_moreSharesThanTheMinimum_raisesError`. Use `default` as condition for the nominal case
  (`test_patch_default_callsProductUpdated`); for views, `<method>` is the HTTP verb (`test_get_loggedInAsNormalMember_returns403`).
- **Mock parameter naming**: the test parameter receiving a patched function or method is named
  `mock_<name_of_the_function>`, e.g. `mock_get_payment_export_exclusion_periods_for_member` for
  `@patch.object(TapirCache, "get_payment_export_exclusion_periods_for_member", ...)`.
- **Mock return values**: set `return_value` / `side_effect` in the test body (`mock_x.return_value = ...`), never in
  the `@patch` / `@patch.object` decorator. Exception: class-level decorators, which may set a default for all tests.
- **Annotate API views** with `@extend_schema(...)` and run `make schema`.
- **Admin docs**: when adding, changing or removing an admin-visible feature, ask whether the admin documentation in
  `docs/admins/` should be updated.
- **Test data generation**: when adding or updating a feature, ask whether test data generation
  (`tapir/utils/services/test_data_generation/`, `populate` command) should be updated. Never write automated tests for
  test data generation.
- **Docs language**: admin documentation (`docs/admins/`) is written in German, developer documentation (`docs/dev/`) in
  English.
- **Formatting**: Black / Prettier / DjHTML, enforced by pre-commit (`poetry run pre-commit install`).
- **Commits**: [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/), referencing the GitHub issue ID
  when applicable.
- **Pull requests**: Pull request names should also follow conventional commits: they will be squashed and the PR's
  title will be used as commit message.