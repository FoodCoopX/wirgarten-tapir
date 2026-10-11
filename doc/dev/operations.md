# Configuration & operations

## Settings layering

[tapir/settings/__init__.py](../../tapir/settings/__init__.py) imports, in order:

1. `base.py` — apps, middleware, templates, DRF, i18n (German defaults), static/Vite, permission-relevant cookie settings.
2. `deployment.py` — everything environment-dependent: DB, Redis/Celery, Keycloak, e-mail, Celery beat schedule, filepond paths, `DEBUG`, `SECRET_KEY`.
3. `site.py` — per-installation specifics; optional, failure to import is only printed.

Values are read with `django-environ` from the real environment and from `.env.local` at the repo root
(template: `.env.local.disabled`). `.env.local` is git-ignored — never commit it.

Two layers of configuration exist and they are not interchangeable:

| | Django settings | `TapirParameter` |
|---|---|---|
| Changed by | ops, via env vars + restart | admins, at runtime in the UI |
| Holds | infrastructure, secrets, endpoints | business rules, feature flags, mail texts |
| Read via | `settings.X` | `get_parameter_value(key, cache)` |

New parameters must be declared in a `ParameterDefinitions*` class and materialised with
`python manage.py parameter_definitions`.

## Services

| Service | Port | Note |
|---|---|---|
| `web` | 8000 | Django (+ `runserver` in dev) |
| `vite` | 5173 | Dev asset server; also the container used to regenerate the TS client |
| `keycloak` | 8080 | Identity provider, realm `tapir` imported from `docker/keycloak/import/` |
| `db` | 5432 | PostgreSQL 14 |
| `redis` | 6379 | Celery broker/result backend **and** Django cache backend |
| `celery`, `celery-beat` | — | Async tasks and the business calendar |

Dev credentials in `docker-compose.yml` and the Keycloak realm import are development-only — see [security.md](security.md).

## Assets: dev vs production

- `DJANGO_VITE_DEBUG=True` → templates load from the Vite dev server with HMR.
- Otherwise Django serves the built bundle from `dist/` via `dist/manifest.json` and WhiteNoise, so production requires `pnpm build` + `collectstatic`.

## E-mail

Three separate paths, documented in detail (German) in [doc/email_administration.md](../email_administration.md):

1. **Transactional/bulk Tapir mail** via `tapir_mail` and SMTP, dispatched in batches by Celery beat.
2. **Bounce detection** via a separate IMAP mailbox.
3. **Login/password/activation mails come from Keycloak**, configured in Keycloak, not in Django.

In the dev environment the e-mail backend writes files instead of sending; if "no mail arrives", look there first.

## Scheduled business processes

`CELERY_BEAT_SCHEDULE` in [tapir/settings/deployment.py](../../tapir/settings/deployment.py) runs, among others,
subscription and solidarity renewals, monthly payment creation, membership mails, mail dispatch batches and cleanup
jobs. Treat these as production business logic: idempotent, in a service class, with their own `cache` dict, and
monitored — `tapir/celery.py` mails admins on task failure.

## Deployment checklist

- [ ] `SECRET_KEY` set from the environment (a hardcoded dev default exists as a fallback).
- [ ] `DEBUG=False` (default) and `ALLOWED_HOSTS` set explicitly — the default is `["*"]`.
- [ ] HTTPS enforced in front of Django: `CSRF_COOKIE_SECURE=True` and `CSRF_COOKIE_SAMESITE="None"` are set, so cookies are only sent over TLS.
- [ ] Keycloak admin client secret, DB password and Keycloak bootstrap admin password replaced; realm import values are dev-only.
- [ ] SMTP/IMAP credentials set; mail backend switched to the production backend.
- [ ] `migrate` and `parameter_definitions` run after every deployment.
- [ ] Frontend built and `collectstatic` run.
- [ ] Database backup before destructive management commands ([doc/import_users.md](../import_users.md)).
- [ ] Celery worker **and** beat running; a missing beat silently stops renewals and payments.
- [ ] Error log directory writable (`GlobalServerErrorHandlerMiddleware`).

## Useful management commands

`populate --reset_all [--org=bakery]` (test data, destructive), `parameter_definitions`, `spectacular --file schema.yml`,
plus the import/cleanup commands described in [doc/import_users.md](../import_users.md).
The optional `ortools` extra enables the bakery baking-plan solver; without it those endpoints answer 503.
