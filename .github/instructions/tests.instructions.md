---
applyTo: "tapir/**/tests/**"
---

# Test rules

Details: [doc/dev/testing.md](../../doc/dev/testing.md).

- `TapirUnitTest` (no DB, runs anywhere) for service/calculator logic; `TapirIntegrationTest` (DB + mocked Keycloak,
  must run inside Docker) for views, permissions and anything persisting data. Both live in
  `tapir/wirgarten/tests/test_utils.py`.
- **Never create users in `setUpTestData`.** The Keycloak mock is installed per test in `setUp`, so users created at
  class level are unknown to it. Use `setUp` or the test method.
- `has_perm()` short-circuits to `is_superuser` under test: a test that only logs in as admin proves nothing about
  authorization. For every permission-guarded or member-scoped endpoint, add a case with a plain member asserting 403.
- Build objects with the app's `tests/factories.py` factories rather than by hand; the domain has many required FKs.
- Pin the dates an assertion depends on — factory defaults based on "today" make tests pass or fail depending on the
  season. Cover before / inside / after for date-ranged logic.
- Celery tasks: assert idempotency (running twice must not duplicate payments or rows).
- `--reuse-db -n auto` is the fast path; drop both flags when debugging. CI runs `make test` (Black check, collectstatic,
  pytest with coverage).
