# Plan: typed request cache (`TapirRequestCache`)

Repo copy: `plans/cache_refactoring_plan.md` (not under `docs/`, which mkdocs publishes).

**Precondition: do not start before these open PRs are merged.** They add new code against the current cache API (`cache: dict`, `cache={}`, string keys, `TapirCache`, `get_from_cache_or_compute`) that would merge cleanly but break once phases 4b and 5 land:
- Bidding round stack (#1311): #1351, #1352 (207 `cache: dict`/`cache={}` lines, direct `cache[...]` string keys), #1353, #1354, #1355, #1356, #1357, and #1386.
- Deposit stack (#1325): #1366, #1369, #1370, #1373, #1376, #1382, #1383.

Before starting, run `gh pr list` and make sure no other big PRs have been opened in the meantime, in particular ones adding code against the current cache API. If there are, wait for them too or list them here.

## Progress
Tick a box right after finishing the step, in both the plan file and the repo copy.

- [x] Phase 0 — copy plan to repo
- [ ] Phase 1 — core class `TapirRequestCache` / `TapirCacheKey` + tests
- [ ] Phase 2 — swap the type everywhere
- [ ] Phase 3 — convert keys
  - [ ] `tapir/utils/services/tapir_cache.py`
  - [ ] `tapir/configuration/parameter.py` + `mock_parameter_value`
  - [ ] `tapir/wirgarten/service/products.py`
  - [ ] `tapir/pickup_locations/services/*` (incl. `pickup_location` key split)
  - [ ] `tapir/subscriptions/services/automatic_subscription_renewal_service.py`
  - [ ] `tapir/payments/services/mandate_reference_provider.py`
  - [ ] `tapir/core/services/mailman/tapir_mailman_client.py`
  - [ ] remaining modules
- [ ] Phase 4 — invalidation
  - [ ] replace the 9 `clear_category` calls
  - [ ] audit for missing invalidations + regression tests
- [ ] Phase 4b — split `TapirCache` by domain
- [ ] Phase 5 — remove legacy
  - [ ] drop `dict` base, delete `TapirCacheManager` and `get_from_cache_or_compute`
  - [ ] make cache required (remove `= None` defaults)
- [ ] Phase 6 — docs
  - [ ] `AGENTS.md`, `.agents/rules/base-rules.md`, `.agents/agents/code-reviewer.md`
  - [ ] `docs/dev/request_cache.md` + link from `docs/dev/index.md`
- [ ] Phase 7 — evaluate Redis layer

## Context

The per-request query cache is a plain `dict` passed through ~640 signatures (`cache: dict`), created as `{}` at ~220 origins (views, forms, commands, tasks) and ~700 times in tests.

Problems:
- Any dict is accepted; the cache has no distinct type.
- Values are untyped: `get_from_cache_or_compute` (`tapir/utils/shortcuts.py:46`) is generic over the compute function only.
- 65 top-level string keys, only 9 registered in a category via `TapirCacheManager.register_key_in_category` (`tapir/utils/services/tapir_cache_manager.py`). Invalidation (`clear_category`, 9 call sites) misses every unregistered key that depends on the cleared data.
- Key collision: `member_pickup_location_getter.py:105`, `pickup_location_highest_usage_after_date_service.py:61` and `share_capacities_service.py:28` all use the `PickupLocation` instance as top-level key and share its sub-dict. Clearing `CATEGORY_MEMBER_PICKUP_LOCATIONS` wipes all three; `date_of_last_possible_capacity_change` is only invalidated on subscription changes by accident.
- The reserved `"categories"` key lives inside the same dict as the values.
- `mandate_reference_provider.py:32` mutates the dict directly.

## Design decisions

### Keys are constants — typed key objects, not strings

```python
@dataclass(frozen=True, eq=False)
class TapirCacheKey[T]:
    name: str
    depends_on: frozenset[type[Model]]
```

- `name` must be unique: `__post_init__` registers it in a module-level set and raises on a duplicate (import-time error). This is the collision guarantee, and the stable identifier for a possible shared-cache layer (phase 7). Caveat: importing the same key module twice (`importlib.reload`, a module importable under two paths) raises a false duplicate.
- `eq=False` → identity hash: cheaper than hashing `name` + `depends_on` on every `get_or_compute`. Performance only, not needed for correctness.
- Generic `T` types the stored value; `get_or_compute` returns `T`.
- Declared next to their single user as class constants (`TapirCache.SUBSCRIPTIONS_BY_DATE`, `ShareCapacitiesService.CAPACITIES_BY_PICKUP_LOCATION`, …). No central key module: it would import models from every app and invite import cycles.
- Argument-dependent lookups stay a plain inner dict under one top-level key, read with `dict_get_or_set` (`tapir/utils/shortcuts.py:54`):
  ```python
  by_date = cache.get_or_compute(key=cls.SUBSCRIPTIONS_BY_DATE, compute=dict)
  return dict_get_or_set(by_date, reference_date, compute)
  ```

### Every key is forced into a category — categories are Django models

- `depends_on` is a required constructor argument → missing it is a type/IDE error.
- `__post_init__` raises on an empty `depends_on` → caught at import time, i.e. by any test run.
- Registration happens inside `get_or_compute`; no separate registration call to forget.
- Invalidation: `cache.invalidate(model=Subscription)` replaces `clear_category`. Mapping of existing categories:
  - `CATEGORY_SUBSCRIPTIONS` → `Subscription`
  - `CATEGORY_MEMBER_PICKUP_LOCATIONS` → `MemberPickupLocation`
  - `CATEGORY_PAYMENT_RHYTHMS` → `MemberPaymentRhythm`

### Transitive dependencies are derived, not declared

`TapirRequestCache` keeps a stack of keys being computed. Every `get_or_compute` (hit or miss) adds the read key's effective dependencies to all keys on the stack. Effective dependencies are stored per entry and used by `invalidate`. A key's `depends_on` therefore only lists the models its own ORM queries read (e.g. `get_today` → parameters → `TapirParameter` propagates automatically).

## Implementation

### Phase 0 — copy this plan to the repo
Write this file to `plans/cache_refactoring_plan.md`.

### Phase 1 — core class
New `tapir/utils/services/tapir_request_cache.py`:

```python
class TapirRequestCache(dict):  # dict base is temporary, removed in phase 5
    def get_or_compute[T](self, key: TapirCacheKey[T], compute: Callable[[], T]) -> T: ...
    def invalidate(self, model: type[Model]) -> None: ...
```

Internal state: `_values: dict[TapirCacheKey, Any]`, `_dependencies: dict[TapirCacheKey, set[type[Model]]]`, `_computing: list[TapirCacheKey]`. A compute that raises must pop the stack (`try/finally`) and store nothing.

Tests in `tapir/utils/tests/services/tapir_request_cache/`, one file per method (`test_get_or_compute.py`, `test_invalidate.py`), subclassing `TapirUnitTest`. Cover: hit/miss, typed return, empty `depends_on` raises, duplicate `name` raises, transitive dependency propagation (also on a hit inside a compute), invalidation of only dependent keys, exception during compute.

### Phase 2 — swap the type everywhere (mechanical)
The temporary `dict` base keeps all existing `get_from_cache_or_compute(cache, "…")` and `TapirCacheManager` calls working.
- `cache: dict` / `cache: dict | None` → `cache: TapirRequestCache` (script over `tapir/`, excluding `migrations/`).
- `cache = {}` / `cache={}` → `TapirRequestCache()` in origins (views `__init__`, forms, commands, celery tasks, serializer contexts) and in tests.
- `tapir/utils/tests_utils.py:mock_parameter_value` takes `TapirRequestCache`.

### Phase 3 — convert keys, module by module
For each top-level `get_from_cache_or_compute(cache, "<key>", …)`:
1. Declare a `TapirCacheKey` constant on the owning class with its direct `depends_on`.
2. Replace the call with `cache.get_or_compute(key=…, compute=…)`; inner per-argument lookups use `dict_get_or_set`.
3. Drop the matching `register_key_in_category` call.

Order: `tapir/utils/services/tapir_cache.py` (83 calls), then `tapir/configuration/parameter.py` (`parameters_by_key`, `parameter_cache`; update `mock_parameter_value` in the same step), `tapir/wirgarten/service/products.py`, `tapir/pickup_locations/services/*`, `tapir/subscriptions/services/automatic_subscription_renewal_service.py`, `tapir/payments/services/mandate_reference_provider.py`, `tapir/core/services/mailman/tapir_mailman_client.py`, the rest.

Specific fixes along the way:
- Split the shared `cache[pickup_location]` into three keys (members at date, last possible capacity change, share capacities by product type), each a dict keyed by pickup location id.
- `mandate_reference_provider.py:32`: append the new mandate ref through the value returned by `get_or_compute` instead of `cache.get(CACHE_KEY)`.
- `tapir_mailman_client.py`: external API, no model dependency → decide a model (e.g. `Member`) or allow an explicit `depends_on=frozenset({ExternalData})` marker; resolve when converting it.

### Phase 4 — invalidation sites
Replace the 9 `TapirCacheManager.clear_category(...)` calls with `cache.invalidate(model=...)`:
`member_payment_rhythm_service.py:229`, `member_pickup_location_setter.py:71`, `apply_tapir_order_manager.py:72,128`, `subscription_date_change_applier.py:174`, `wirgarten/forms/member.py:480`, `wirgarten/forms/subscription.py:405,820`, `wirgarten/views/member/details/actions.py:84`.

Then audit for missing invalidations (today only 3 models are ever invalidated; after phase 3 keys depend on many more):
1. Collect every model appearing in any key's `depends_on`.
2. Find writes to those models in code holding a cache: `.save()`, `.objects.create`, `bulk_create`, `bulk_update`, `queryset.update()`, `.delete()`.
3. For each write, check whether the same cache instance is read afterwards in the same request/command/task. Only then add `cache.invalidate(model=...)` right after the write. A write that ends the flow needs none.
4. Each added invalidation gets a regression test: read → write → read again, assert the fresh value.

Invalidation stays manual: no signal- or contextvar-based automatic invalidation.

### Phase 4b — split `TapirCache` by domain (pure move)
`tapir/utils/services/tapir_cache.py` holds 56 accessors over ~10 domains and imports models from 10 apps: a utils module depending on every feature app (import-cycle risk, keys' `depends_on` far from their models, merge conflicts).

- `TapirRequestCache` and `TapirCacheKey` stay in `tapir/utils/services/` (no model imports).
- Accessors and their `TapirCacheKey` constants move to one `<Domain>Cache` class per app in `<app>/services/<domain>_cache.py`, e.g.:
  - `SubscriptionCache` (subscriptions, solidarity contributions, notice periods) → `tapir/subscriptions/services/`
  - `ProductCache` (products, product types, prices, tax rates, capacities, basket size equivalences) → `tapir/products/services/`
  - `PickupLocationCache` (pickup locations, opening times, routes, delivery charges) → `tapir/pickup_locations/services/`
  - `GrowingPeriodCache`, `PaymentCache` (rhythms, payments, credits, exclusion periods), `DeliveryCache` (jokers, adjustments, donations, custom cycles), `AssociationCache`, `CoopCache`, `BakeryCache` → their apps
  - Exact grouping decided per accessor by the models it reads.
- Accessors for models in legacy `tapir.wirgarten.models` go to the feature app, never to `wirgarten`.
- Classes stay cache façades: one accessor per cached query, no business logic.
- Mechanical diff only: move code, update ~140 caller imports (`TapirCache.x` → `<Domain>Cache.x`), no behaviour change. Delete `tapir_cache.py` when empty.
- Tests for moved accessors move with them.

### Phase 5 — remove legacy
- Drop the `dict` base of `TapirRequestCache`.
- Delete `TapirCacheManager` and `get_from_cache_or_compute` (inner lookups already use `dict_get_or_set`). Leave the frozen copy in `tapir/solidarity_contribution/migrations/0002_auto_20251212_1036.py` untouched.
- Make the cache required: remove `= None` defaults and `if cache is None` branches (46 non-test signatures, e.g. `get_parameter_value`, `get_today`, `get_now`, `tokenize_parameter`, `coop/tasks.py`).

### Phase 6 — docs and conventions
Update the `cache` paragraph in `AGENTS.md:110`, `.agents/rules/base-rules.md:110` and the cache bullet in `.agents/agents/code-reviewer.md:30`: type `TapirRequestCache`, keys are `TapirCacheKey` constants with `depends_on`, invalidate by model after writes.

**Should the dev docs be updated? Yes.** `docs/dev/` currently holds only `index.md` (placeholder) and `frontend_dates.md`; nothing documents the cache. The agent files above are terse rules for agents; human contributors need the reasoning. Add `docs/dev/request_cache.md`, modelled on `frontend_dates.md`:
- What the cache is for (per-request query cache) and where to create it (view `__init__`, form, command, task start).
- Declaring a key: `TapirCacheKey[T]` constant on the owning class, `depends_on` = models read by its own queries; transitive dependencies are derived.
- Per-argument lookups: one top-level key holding a dict + `dict_get_or_set`.
- Invalidation: `cache.invalidate(model=...)` after writes within the same request.
- Tests: `TapirRequestCache()` per test, `mock_parameter_value`.

Link it from `docs/dev/index.md`. Note: `mkdocs.yml` publishes all of `docs/` (awesome-pages), so this page becomes part of the published site alongside `frontend_dates.md`.

### Phase 7 — consider a Redis layer (evaluation only)
Once phases 0–6 are done, evaluate an opt-in second level in Redis (already the Django cache backend) behind `TapirRequestCache.get_or_compute`: request cache → Redis → compute. Decide whether it's worth it; no implementation in this plan. Points to settle:
- Cross-process invalidation: manual `invalidate` only covers same-flow reads. Options: per-model version counters in Redis bumped on every write, or TTL-only staleness. Automatic signal-based invalidation stays excluded.
- Which keys: only expensive derived values (capacity usage, dashboard aggregates); not whole-table loads like `all_subscriptions`, where unpickling costs about as much as the query.
- Granularity: per-argument entries (key `name` + args) instead of whole inner dicts.
- Time-dependent values (`get_today`/`get_now`, test date override) need the date in the key.
- Cached values must be treated as immutable.
- Measure first: kgz admin dashboard TTFB baseline ~0.68 s.

## Verification
- After each phase: full test suite (`.env.local` present → host, else `docker compose exec -T web poetry run pytest --reuse-db -n 6`), `pre-commit run --files <edited>`.
- After phase 5, these greps return nothing outside `migrations/`: `cache: dict`, `get_from_cache_or_compute`, `TapirCacheManager`, `TapirCache.`, `cache={}`, `cache = {}`.
- Manual check of an invalidation path: change a member's pickup location in the member profile, confirm the capacity display updates in the same request flow (previously relied on the shared sub-dict).
- Perf sanity: kgz admin dashboard TTFB stays around the ~0.68 s baseline.
