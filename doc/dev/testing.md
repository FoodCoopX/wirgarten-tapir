# Testing

pytest + pytest-django + factory-boy. Commands are in [README.md](../../README.md); this document covers the rules that
are not obvious.

## Layout

```
tapir/<app>/tests/
├── factories.py          factory-boy factories for the app's models
├── unit/        test_*.py   no DB, no HTTP  → run anywhere
└── integration/ test_*.py   DB + Keycloak mock → run inside Docker
```

Not every app uses the `unit/` / `integration/` split, but every new test should pick a side consciously.

| Base class | From | Use for |
|---|---|---|
| `TapirUnitTest` | [tapir/wirgarten/tests/test_utils.py](../../tapir/wirgarten/tests/test_utils.py) | Pure logic: calculators, validators, date maths. Based on `SimpleTestCase`, no DB. |
| `TapirIntegrationTest` | same file | Anything touching the DB, views, permissions, mails. Based on `TestCase`; sets up `Client`, `APIClient`, clears the cache, configures the mail module and **mocks Keycloak**. |

## The Keycloak rule

`TapirIntegrationTest.setUp()` installs the Keycloak mock (`mock_keycloak`), which keeps an in-memory
e-mail → fake-id mapping. `setUpTestData()` runs **once per class, before `setUp`**, so users created there exist in the
DB but are unknown to the per-test mock, and later operations that resolve a Keycloak id fail.

> **Create users (and anything that creates users, e.g. `MemberFactory`) in `setUp` or in the test method — never in `setUpTestData`.**

Second consequence: `KeycloakUser.has_perm()` short-circuits to `is_superuser` under test. A test that only logs in as
admin proves nothing about authorization. Add a case with a plain member for every member-scoped or permission-guarded
endpoint.

## Factories

Every app has `tests/factories.py` with `factory.django.DjangoModelFactory[Model]` subclasses, e.g. `MemberFactory`,
`MemberWithSubscriptionFactory`, `SubscriptionFactory`, `ProductPriceFactory`, `GrowingPeriodFactory`,
`PickupLocationFactory`. Prefer composing existing factories over building objects by hand — the domain has many
required FKs and date ranges.

Because the domain is date-driven, a factory default of "today" can make a test pass in March and fail in December.
Pin the dates your assertion depends on explicitly.

## What to test

| Layer | Test |
|---|---|
| Service | Unit tests for the business rules, including boundary dates (start, end, trial end, notice period) |
| View | Integration test for happy path, validation errors, **and** 403 for a non-privileged user |
| Celery task | Idempotency: running it twice must not double-charge or duplicate rows |
| Dated data | At least one test with a `reference_date` before, inside and after the range |

## Running

- Unit tests run outside Docker with the Poetry environment; integration tests must run inside the `web` container.
- `--reuse-db -n auto` is the fast path; drop both flags when debugging confusing failures.
- `make test` is what CI runs: `black --check`, `collectstatic`, then pytest with coverage.
- CI ([.github/workflows/tests.yml](../../.github/workflows/tests.yml)) runs `docker compose run web make test` and uploads coverage to SonarCloud.
