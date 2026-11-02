---
name: add-frontend-entry
description: Adds a new React island to the Vite build and renders it from a Django template. Use when creating a new frontend feature page, or when a newly added *_entry.tsx renders nothing / 404s on its asset.
---

# Add a React entry point

The frontend is not an SPA: each feature is a React island mounted into a DOM node of a Django
template. A new feature needs three things that must match each other, and forgetting one of them
is the usual cause of "my component does not render".

## 1. The entry file

Create `src_frontend/<feature>/<feature>_entry.tsx`. It mounts into a node that the template
renders:

```tsx
import { createRoot } from "react-dom/client";
import MyFeature from "./MyFeature";

const root = document.getElementById("my_feature");
if (root) createRoot(root).render(<MyFeature />);
```

Fetch data through `src_frontend/hooks/useApi.ts` — it injects the CSRF token and the base path
from `env.ts`. There is no Redux/Zustand and no path aliases, so import with relative paths.

## 2. Register it in the Vite build

Add the entry to `rollupOptions.input` in `vite.config.ts`. The key is the bundle name, the value
is the path below `INPUT_DIR`:

```ts
my_feature: join(INPUT_DIR, "/my_feature/my_feature_entry.tsx"),
```

An entry that is missing here is never built, and `vite_asset` will fail for it.

## 3. Load it from the Django template

```html
{% extends "core/base.html" %}
{% load django_vite %}
{% block head %}
    {% vite_asset 'my_feature/my_feature_entry.tsx' %}
{% endblock head %}
{% block content %}
    {% csrf_token %}
    <span id="my_feature"></span>
{% endblock content %}
```

The path passed to `vite_asset` is relative to `src_frontend/` and must be exactly the path used in
`vite.config.ts`. The `id` must be exactly the one the entry looks up. Keep `{% csrf_token %}` when
the island writes data.

## 4. Check

- Restart the `vite` container after editing `vite.config.ts` — the input list is read at startup.
- Templates are formatted by DjHTML via pre-commit; run `poetry run pre-commit run --files <file>`
  if indentation is flagged.
