---
applyTo: "tapir/**/*.py"
---

# Backend rules (Django/DRF)

Details: [doc/dev/architecture.md](../../doc/dev/architecture.md), domain rules in
[doc/dev/domain-model.md](../../doc/dev/domain-model.md), risky areas in [doc/dev/security.md](../../doc/dev/security.md).

- Business logic goes into `tapir/<app>/services/` as a class with `@classmethod`s named `<Verb><Noun>`
  (`...Creator`, `...Validator`, `...Calculator`). Views parse and serialize only; models hold their own fields.
- Services take `cache: dict` as a **required** parameter and pass it down. Create exactly one `cache` per
  request/task/command at the outermost layer — never a fresh `{}` deeper in the stack. After a write that invalidates
  cached data in the same request, call `TapirCacheManager.clear_category(...)`.
- New models inherit `tapir.core.models.TapirModel` and live in the owning app, never in `tapir/wirgarten/`
  (legacy — when you must change it, extract the touched part into a non-legacy app).
- Authorization: `user.has_perm("coop.manage")` checks **Keycloak roles**; use the constants in
  `tapir/wirgarten/constants.py`. Set `permission_classes` explicitly on every DRF view. Whenever a `member_id` comes
  from the URL, query or body, call `check_permission_or_self(...)` from `tapir/wirgarten/utils.py`.
- Never accept prices, amounts, capacities or entitlements from the client — recompute them server-side from the DB.
- Annotate every API view with `@extend_schema(...)`, then regenerate `schema.yml` **and** the TS client and commit both.
- Dates: most data is date-ranged (`valid_from` / `valid_at` / `start_date`+`end_date`). Accept an optional
  `reference_date` defaulting to `get_today()`; a set `cancellation_ts` does not mean inactive; a null `end_date` means
  open-ended. Edit dated records by inserting a new row, not by rewriting history.
- Money is `Decimal` (`max_digits=8, decimal_places=2`). Never use `float`.
- Runtime configuration goes through `TapirParameter` (`get_parameter_value(key, cache)`), declared in a
  `ParameterDefinitions*` class and materialised with `manage.py parameter_definitions`.
- Prefer explicit `fields = [...]` in serializers over `fields = "__all__"`; mark `id`, timestamps and status fields
  read-only.
- No raw SQL outside migrations. Log admin changes to member data via the `log` app, excluding secrets.
- Format with Black. Commit messages: conventional commits with the GitHub issue id.
