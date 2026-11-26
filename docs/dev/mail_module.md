# Mail module

!!! warning "The mail module may not follow all of Tapir's conventions"
    The mail module was developed as a separate, standalone package, with its own dummy accounts and test
    setup, and was moved into Tapir later without a full refactoring. Parts of it don't follow Tapir's
    conventions yet: the cache parameter, service classes, the test layout, one test class per file,
    keyword arguments, validation outside of serializers, …

    Update the code as you go: when you touch a part of the mail module, bring that part in line with
    Tapir's conventions. New code follows Tapir's conventions from the start.









## Frontend

### Separate package on React 18

`src_frontend_mail` is its own pnpm workspace package with its own `package.json`, and it stays on React 18.
The mail editor is built with [easy-email](https://github.com/zalify/easy-email-editor), which only supports
React 18.

Consequences of the separate package:

- **Build:** the root `pnpm build` builds the main frontend into `dist/` and then the mail package into
  `dist/mail/`. The root Vite build empties `dist/` including `dist/mail/`, so running only the root Vite build
  removes the mail build.
- **Dev servers:** the `vite` container runs both, on 5173 (main) and 5174 (mail). django-vite uses the
  `"mail"` config for the mail entry (`tapir/settings/base.py`). The mail Vite config sets `server.origin`, so
  that URLs inside CSS (e.g. fonts) point to the dev server instead of Django.
- **React types:** pnpm hoists the root's `@types/react` 19, which third-party typings in the mail package
  would otherwise pick up. `src_frontend_mail/tsconfig.json` pins `react` and `react-dom` to the package's own
  React 18 types via `paths`.
- **No code sharing with `src_frontend` except the API client:** components and hooks from `src_frontend`
  would load React 19 from the root, so the mail UI has its own copies (e.g. `TapirButton`, `useApi`). The
  generated API client has no React dependency, so the mail UI imports it from `src_frontend/api-client`
  through the `tapir-api-client` alias.

### Workarounds for easy-email

- **CSS minification:** the Arco theme bundled with easy-email contains invalid CSS that Vite's default
  minifier (lightningcss) rejects, so the mail package minifies CSS with esbuild.
- **Body font:** the Arco theme sets the `body` font and size, which would also change Tapir's header and
  sidebar on the mail pages. `src_frontend_mail/src/index.css` resets them to Bootstrap's.
- **Editor fonts:** the editor's web fonts are referenced as `/static/fonts/…` and live in
  `tapir/mail/static/fonts/`.

### Configuration and URLs

- `MailUiView` writes the mail UI's configuration into `window._env_`: `REACT_APP_API_ROOT` (`SITE_URL` +
  `/tapirmail`) and `REACT_APP_BASENAME` (`/tapirmail`, the router's basename).
- The generated client already contains `/tapirmail` in every path, so `useApi` uses an empty base path.
  `REACT_APP_API_ROOT` is still needed for the media library and filepond URLs, which must be absolute
  because they end up in mails.
- The prefix is the constant `MAIL_URL_PREFIX` in `tapir/mail/config.py`. Changing it requires regenerating
  `schema.yml` and the API client (`make schema`), because the prefix ends up in every generated path and
  operation name.

## Backend

### App label

The code lives in `tapir.mail`, but its app label is `tapir_mail`, set in `TapirMailConfig`. That keeps the
table names, the migration history, content types and permissions from the time the module was a separate
package. Model references in migrations and `apps.get_model` use the label: `apps.get_model("tapir_mail", …)`.

### Redis in tests

The dispatch tasks use `django_redis` locks, so the mail tests need a real Redis. `tapir/conftest.py` gives
each pytest-xdist worker its own Redis database, because `cache.clear()` flushes the whole database.

