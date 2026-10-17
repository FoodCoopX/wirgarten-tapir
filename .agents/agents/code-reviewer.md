---
name: code-reviewer
description: Reviews changes against this repository's architecture conventions — service classes, the cache parameter, the legacy wirgarten app, schema annotations and test placement. Use before opening a pull request or when asked to review a diff.
---

# Code reviewer

Review the diff against the repository conventions. Report findings, do not change code unless
asked.

## How to get the diff

```bash
git diff --merge-base origin/master
```

Read [base-rules.md](../rules/base-rules.md) first if you don't already have the repo map in
context.

## What to check

**Architecture**

- Business logic belongs in a service class under `tapir/<app>/services/`, not in views, models or
  serializers.
- Models inherit `tapir.core.models.TapirModel`. Model methods may only reference fields of that
  same object; anything that needs other objects belongs in a service.
- New code must not be added to `tapir/wirgarten/` — it is legacy. If the change touches it, ask
  whether the affected part can be moved into the app that owns the domain.
- Service functions that hit the DB repeatedly should take the `cache` dict and pass it down
  instead of re-querying. The cache is created at the origin (view `__init__`, start of a command).

**API**

- New or changed DRF views are annotated with `@extend_schema(...)`.
- If a serializer or view changed, `schema.yml` and `src_frontend/api-client/` must be regenerated
  — see the `regenerate-api-client` skill. Neither is hand-edited.

**Frontend**

- A new entry point is registered in `vite.config.ts` and loaded from a Django template — see the
  `add-frontend-entry` skill.
- Data fetching goes through `src_frontend/hooks/useApi.ts`. No new state management library, no
  path aliases.

**Tests**

- Tests live in `tapir/<app>/tests/`, with factory-boy factories in `factories.py`.
- Integration tests subclass `TapirIntegrationTest`, which mocks Keycloak in `setUp` — so users
  must not be created in `setUpTestData`.
- Changed behaviour has a test that would fail without the change.

**Commits**

- [Conventional commits](https://www.conventionalcommits.org/en/v1.0.0/), referencing the GitHub
  issue ID when there is one.

## Output

Group findings by severity (blocking / should fix / nitpick). For each one give the file, the line
and a concrete fix. Say so explicitly when the diff looks good — don't invent findings.
