---
name: regenerate-api-client
description: Regenerates schema.yml and the generated TypeScript API client in src_frontend/api-client after changing a DRF view, serializer or route. Use whenever a backend API surface changed, or when the frontend reports missing or outdated client types.
---

# Regenerate the API schema and TypeScript client

`schema.yml` and `src_frontend/api-client/` are **generated artifacts**. Never edit them by hand —
change the DRF view or serializer and regenerate.

## When this is needed

Any change to a serializer, an API view, a DRF router registration or an `@extend_schema`
annotation. Both generated outputs are committed, so they must be regenerated in the same commit.

## Steps

1. Make sure the view is annotated, otherwise the generated client is useless:

   ```python
   @extend_schema(responses={200: MySerializer(many=True)})
   def get(self, request): ...
   ```

2. Regenerate the schema from inside the `web` container, then the client from inside `vite`:

   ```bash
   docker compose exec web ./scripts/generate_api_schema.sh \
     && docker compose exec vite ./scripts/generate_api_clients.sh
   ```

   The schema step runs `manage.py spectacular --file schema.yml`. The client step is a no-op when
   `schema.yml` is unchanged — it compares an md5 hash stored in `.schema.hash` and prints
   `API client up to date (schema.yml unchanged)`.

3. Check the result:

   ```bash
   git status --short schema.yml src_frontend/api-client .schema.hash
   ```

   Commit `schema.yml`, `.schema.hash` and the regenerated client together with the backend change.

## Notes

- The containers must be running (`docker compose up`, or `./scripts/reset_all_containers.sh` for a
  full reset).
- The client generator writes imports that do not resolve, which would break `npm run build`; the
  script already runs Prettier with an import organiser afterwards to clean them. Don't skip it by
  calling `openapi-generator-cli` directly.
- Generated client files are marked `linguist-generated` in `.gitattributes`, so GitHub collapses
  them in diffs. A large diff there is expected and fine.
