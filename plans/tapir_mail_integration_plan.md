# Plan: move the mail module into Tapir

Repo copy: `plans/tapir_mail_integration_plan.md` (not under `docs/`, which mkdocs publishes).

## Goal

The code of `tapir-mail-module` (`../tapir-mail-module`) lives in this repo. Tapir no longer installs the `tapir-mail` wheel from `FoodCoopX/tapir-mail-releases`, and mail changes no longer need a release round-trip.

Out of scope: refactoring the mail code to Tapir's conventions (cache parameter, service classes, test layout). That happens in follow-ups, after the code is in place.

## React 19 vs. easy-email

**Result: easy-email can't run on React 19, and Tapir doesn't need to downgrade.** The mail UI becomes its own pnpm workspace package that keeps React 18. The rest of Tapir stays on React 19.

Findings:
- `easy-email-core` / `-editor` / `-extensions` 4.17.1 (latest, June 2026) declare `react: ^18.2.0` as a peer.
- `easy-email-extensions/lib/index2.js` bundles its own copy of Arco Design. That copy calls APIs that React 19 removed:
  - `ReactDOM.render`: used by Message, Notification and `Modal.confirm`.
  - `ReactDOM.unmountComponentAtNode`.
  - `findDOMNode`, 16 call sites: `Trigger` (every popover, tooltip and dropdown), `ResizeObserver` and `CSSTransition`.

  On React 19, these calls throw `TypeError`s as soon as the editor opens a popup. Arco's React 19 adapter doesn't help, because it only patches the standalone `@arco-design/web-react` package, not the copy bundled here.
- easy-email requires `react-final-form` ^6.5.7, whose peer range ends at React 18. Version 7 supports React 19 but needs `final-form` 5, while easy-email depends on `final-form` 4.
- Downgrading Tapir instead would mean going back from `react-leaflet` 5 (which requires React 19) to 4.x and its `@types`. It would also block every later React upgrade until easy-email is replaced.

Rejected: polyfilling `findDOMNode` / `render` onto React 19. It is fragile and would break silently on React updates.

## Target layout

| What | From (`tapir-mail-module`) | To |
|---|---|---|
| Django app | `tapir_mail/` | `tapir/mail/` (`name="tapir.mail"`, `label="tapir_mail"`) |
| Backend tests | `tapir_mail/tests/` | `tapir/mail/tests/` |
| Mail UI | `tapir_mail_ui/` (CRA, npm) | `src_frontend_mail/`, a pnpm workspace package (Vite, React 18) |
| Dropped | `tapir_mail_server/` (standalone settings, `dummy_accounts`, segments), `Dockerfile-*`, `docker-compose.yml`, release/bundle workflows, `scripts/bundle.sh`, `tapir_mail/__ui__`, `tapir_mail/__static__` | — |

The label stays `tapir_mail`, so the following stay valid without data migrations: table names, migration history, content types, permissions and the `app_label` references in existing migrations.

## Backend

- Copy `tapir_mail/` to `tapir/mail/` and rewrite all imports, including the ~99 files in Tapir and the module's own migrations: `tapir_mail.` → `tapir.mail.`. Set `label = "tapir_mail"` on `TapirMailConfig`.
- `INSTALLED_APPS`: `"tapir_mail"` → `"tapir.mail"`. `urls.py`: `include("tapir.mail.urls")`.
- Celery task names change with the module path: `tapir_mail.tasks.*` → `tapir.mail.tasks.*`. Update the beat schedule in `tapir/settings/deployment.py`. Tasks queued under the old names during the deploy are lost, which is acceptable because every task is periodic and catches up on its next run.
- `pyproject.toml`: remove `tapir-mail`. Add the module's dependencies that Tapir doesn't declare itself: `flufl-bounce`, `beautifulsoup4`, `django-drf-filepond` and `django-cors-headers` (check each, some may already be in the lock file as transitive dependencies). Run `poetry lock`.
- Settings: remove `get_tapir_mail_template_dir` / `get_tapir_mail_static_dir` and their entries in `TEMPLATES` / `STATICFILES_DIRS`. Move the module's own settings defaults (`STATIC_SEGMENTS`, `EMAIL_TOKENS_STRICT_VALIDATION`, …) into `tapir/settings` if Tapir doesn't set them yet.
- Tests:
  - Seven integration/unit tests use `tapir_mail_server.dummy_accounts`. Rewrite them against Tapir's `Member` factories and segments, or delete them where Tapir's own tests already cover the case.
  - The rest needed adapting: Tapir's test base classes, parameter definitions in `setUpTestData` wherever Tapir's tokens or segments are resolved, `reverse()` instead of hardcoded `/api/...` paths, admin login for the API tests.
  - Tapir's pytest `testpaths = "tapir"` already picks them up.
- `static_segments` management command: keep.

## Frontend

### Workspace package `src_frontend_mail/`

- Own `package.json` containing React 18, `react-dom` 18, `@types/react` 18, easy-email, the Arco theme, `react-final-form` 6, filepond, `react-router-dom` and `framer-motion`. Add the package to `pnpm-workspace.yaml`. pnpm keeps its `node_modules` isolated from the root's React 19.
- Replace CRA with Vite:
  - Own `vite.config.ts` with `root: src_frontend_mail`, `base: "/static/mail/"`, `outDir: dist/mail`, its own `manifest.json`, and dev server port 5174.
  - Drop `react-scripts`, `web-vitals` and `reportWebVitals`.
  - Rename `.js` files with JSX to `.jsx` / `.tsx`.
  - Use `jsx: "react-jsx"` and the same strict tsconfig as `tsconfig.app.json`.
- Root `package.json` `build`: `tsc -b && vite build && pnpm --filter tapir-mail-ui build`. Same for `lint` and the Prettier config, which apply to the new package too.
- API client:
  - The mail viewsets are already mounted in Tapir's `urls.py`, so `schema.yml` contains them.
  - The mail UI imports Tapir's generated client from `src_frontend/api-client` through a Vite/tsconfig alias. The generated client has no React dependency, so sharing it across the React 18 / 19 boundary is safe.
  - Delete `tapir_mail_ui/src/api_client` and fix renamed operations at compile time.
- Frontend tests: deleted. Tapir has no frontend test runner; the old Jest tests stay in the archived mail repo.
- Dropped with the standalone server: the dummy accounts pages and their routes.
- The editor's web fonts are referenced as `/static/fonts/...`; they live in `tapir/mail/static/fonts/` so that URL keeps working.

### Serving

- `django-vite`: a second config `"mail"` with `manifest_path: ./dist/mail/manifest.json`, `static_url_prefix: "mail"` and `dev_server_port: 5174`. `dist/mail/` is served at `/static/mail/` through the existing `STATICFILES_DIRS = ["dist"]`.
- `tapir/mail/templates/tapir_mail/ui.html` extends Tapir's `core/base.html` and loads `main.tsx` via `{% vite_asset ... app="mail" %}`. It replaces the CRA `index.html` in `__ui__`. The mail URLs no longer append their own `static()` route.
- No iframe (decided in phase 7): the mail UI renders inside Tapir's layout at `/tapirmail/…` with real URLs. The mail CSS only loads on the mail pages; `index.css` resets the body font that the Arco theme would otherwise change for Tapir's header and sidebar.
  - `TAPIRMAIL_REACT_APP_API_ROOT` / `_BASENAME` keep working through `env.ts`.
- Docker:
  - `vite.Dockerfile` also copies `src_frontend_mail/package.json` before `pnpm install`.
  - The `vite` service runs both dev servers (`pnpm --parallel --recursive --include-workspace-root run dev`), exposes 5174 and keeps the mail package's `node_modules` in its own volume.
  - `.github/workflows/docker-build.yml` needs no change beyond the root `build` script.

## Docs

New dev page `docs/dev/mail_module.md`, written for a developer who opens the mail code for the first time. Each oddity gets its reason and what would remove it:
- **Separate frontend build**: `src_frontend_mail` is its own workspace package on React 18, because easy-email needs React 18 (see the findings above). Upgrade it independently of the root package. It can join the main build once easy-email is replaced or supports React 19.
- **Body font reset**: the Arco theme bundled with easy-email sets the `body` font and size; `src_frontend_mail/src/index.css` resets them to Bootstrap's, so Tapir's header and sidebar look the same on the mail pages.
- **Shared API client**: the mail UI imports `src_frontend/api-client` across the React 18/19 boundary. This is safe because the generated client doesn't depend on React.
- **Two Vite configs**: the dev servers run on 5173 and 5174, the manifests are `dist/` and `dist/mail/`, and django-vite uses the `"mail"` config for the mail entry.
- **Module path vs. app label**: the code lives in `tapir.mail` but the label is `tapir_mail`, to keep tables, migration history, content types and permissions.
- **Conventions** (as a warning admonition at the top of the page): the mail app may not follow all of Tapir's conventions (cache parameter, service classes, test layout, one test class per file, keyword arguments, …).
  - Why: it was developed as a separate, standalone package with its own dummy accounts and test setup, and was only moved into Tapir later, without a full refactoring.
  - Suggestion: update the code to Tapir's conventions as you go. When touching a part of the mail app, bring that part in line. New code follows Tapir's conventions from the start.
- **Permissions on the views, with a safety-net test**: every mail view requires `Permission.Email.MANAGE` (`HasEmailManagePermission` for DRF views, `PermissionRequiredMixin` for Django views, `DJANGO_DRF_FILEPOND_PERMISSION_CLASSES` for the filepond endpoints), except the public ones listed in `PUBLIC_URL_NAMES` of `tapir/mail/tests/unit/test_MailUrlPermissions.py`. That test fails for any new mail URL that is neither protected nor listed. The mail app imports Tapir's `Permission` constants for this.
- **Global registries**: apps register segment providers, tokens and triggers at startup into module-level registries. Tests that add a segment provider use `add_mail_segment_provider` (`tapir/mail/tests/test_utils.py`), which removes it again on cleanup. Test segment names must not collide with Tapir's (e.g. "Alle Benutzer").
- **Redis in tests**: the dispatch tasks use `django_redis` locks, so the tests need a real Redis. `tapir/conftest.py` gives each xdist worker its own Redis database, because `cache.clear()` flushes the whole database.
- **`tapir.mail` vs. `tapir.wirgarten.tapirmail`**: the mail module is generic; `tapir/wirgarten/tapirmail.py` configures it for Tapir (base segment, tokens, triggers).
- **React 18 types in a React 19 workspace**: pnpm hoists `@types/react` 19 from the root, so third-party typings in the mail package would pick it up. `src_frontend_mail/tsconfig.json` pins `react` / `react-dom` to the package's own `@types` via `paths`.
- **CSS minification with esbuild**: the Arco theme bundled with easy-email contains invalid CSS that Vite's default minifier (lightningcss) rejects.
- **API base path**: the generated client already contains `/tapirmail` in every path, so the mail UI uses an empty base path, while `REACT_APP_API_ROOT` (with `/tapirmail`) is still used for the filepond and media library URLs.
- **Build order**: the root `vite build` empties `dist/`, including `dist/mail/`. The root `pnpm build` therefore builds the mail package last; running only the root Vite build removes the mail build.
- Any further oddity found during phase 6 is added here.

Only the oddities that phase 7 keeps go into the page. For those left for a follow-up, the page names the follow-up.

Other docs:
- `docs/dev/index.md`: link the new page.
- `docs/`: replace mentions of the separate mail repo and its releases.
- `AGENTS.md`: in the app table, add `mail/` with a pointer to `docs/dev/mail_module.md`. Add a short rule: never upgrade React in `src_frontend_mail` together with the root package.

## Evening out oddities (phase 7)

For each oddity, check whether it can be removed with reasonable effort now that the code lives in Tapir. Candidates:
- [x] **Two URL prefixes**: resolved by dropping the iframe; `/mailing/` is gone, UI and API live under `/tapirmail/`.
- [x] **`env.ts` parent-window config**: `MailUiView` renders `window._env_` (API root, basename) into `tapir_mail/ui.html`; `env.ts` only reads it. The `TAPIRMAIL_REACT_APP_*` settings and env vars are gone, and `/tapirmail/…` works without the iframe.
- [x] **Iframe** (replaces "hash syncing by polling"): dropped. The UI renders in Tapir's layout, `TapirMailView` and `tapir_mail_iframe.html` are gone, the editor page grid uses `minmax(0, …)` columns, and the sidebar marks a link as active for its subpages too (`is_path_in_section`). Old `/mailing/#/…` bookmarks are not redirected.
- [x] **`beforeunload` guard in the wrapper**: moved into the mail UI as `usePreventUnload`, used by both editor pages.
- [x] **Dead `NEW_TOKEN` message handler** in `App.tsx`: removed.
- [x] **Duplicate `getCookie` and `credentials: "include"` in `useApi.ts`**: `useApi` uses `utils/cookies.ts`; `credentials: "include"` is dropped (same origin).
- **Mail-specific UI components that duplicate `src_frontend/components`** (`TapirButton`, pagination, modals): reuse is blocked by the React version, so only list them.
- **Settings only the mail module reads**: drop those Tapir never changes from their defaults.
- [x] **`TAPIR_MAIL_PATH` is effectively fixed**: replaced by the constant `MAIL_URL_PREFIX` in `tapir/mail/config.py`; changing it requires regenerating the schema and client.
- **Two `useApi` hooks**: the mail UI has its own copy of `src_frontend/hooks/useApi.ts`. Tapir's hook only uses `useMemo`, which works with React 18 too, so the mail UI could reuse it.
- [x] **Dead CORS settings**: removed from `tapir/settings/base.py`; mail UI and Jasmin checked locally.
- [x] **`STATIC_SEGMENTS` / `static_segments` command**: the command is removed; Tapir never set `STATIC_SEGMENTS`.
- [x] **Path-based permission middleware**: replaced by permissions on the views (see Docs); the middleware, its `MIDDLEWARE` entry and its test are gone, and the routers are `SimpleRouter`s (no API root views).
- [x] **`OnboardingTrigger` ID from the module path**: now `onboarding_trigger`; migration `wirgarten.0153_stable_onboarding_trigger_id` rewrites the stored IDs (forward and backward tests).

Out of scope even if possible: the React 18 package (see above), and refactoring to Tapir's conventions.

## Phases

- [x] Phase 1 — backend move: copy to `tapir/mail/`, label `tapir_mail`, rewrite imports, dependencies, settings, celery task names, drop the wheel
- [x] Phase 2 — backend tests: move, replace `dummy_accounts` usages
- [x] Phase 3 — frontend package: workspace package, CRA → Vite, React 18, shared API client, tests
- [x] Phase 4 — serving: django-vite `mail` config, iframe target template, Docker dev servers, build scripts
- [x] Phase 5 — update dependencies where possible: the npm packages of `src_frontend_mail` and the Python packages the mail app brought in (`beautifulsoup4`, `django-drf-filepond`, `django-redis`, `flufl-bounce`). Within the constraints: React 18 and everything pinned by easy-email (`react-final-form` 6 / `final-form` 4), and pnpm's `minimumReleaseAge`. Major updates (e.g. `react-router-dom` 7, `framer-motion` → `motion`) only if the code changes stay small; otherwise list them as follow-ups. Before the smoke test, so it covers the updates.
  - Updated: `react-router-dom` 7, `react-spinners` 0.17, `@fortawesome/fontawesome-free` 7, minor updates within the ranges, `flufl-bounce` 6 (drops `zope-interface`).
  - Removed: `framer-motion`, which only faded between pages.
  - Kept: React / `react-dom` / `@types` 18 and `react-final-form` 6 (easy-email), `mjml-browser` 4 (easy-email's peer range is `^4`), `filepond` 4 (5 is a beta), TypeScript 6 (same as the root package).
- [x] Phase 6 — smoke test on a local instance: editor popups/tooltips, media library upload, dispatch, bounce check, category registration pages
  - Checked in the browser (dev mode, through the `/mailing/` iframe): dashboard, email configuration editor (easy-email toolbar and popovers), template editor, segment picker, date picker, categories modal, media library upload and delete, test mail, public category registration. A transactional mail went through the Celery tasks to Mailpit.
  - Not checked live: the bounce check (no IMAP mailbox locally; unit tests only).
  - Found and fixed: trigger IDs were derived from the module path, so the move broke every stored trigger. `TransactionalTrigger` and `TimeTrigger` now use stable IDs, migration `0052_stable_trigger_ids` rewrites the stored ones (with forward and backward tests).
  - Found and fixed: in Vite dev mode, URLs inside CSS (Font Awesome fonts) pointed to Django instead of the dev server; `server.origin` in the mail Vite config.
- [ ] Phase 7 — evening out oddities: go through the oddities listed under Docs plus those found in phases 1–6. For each one, decide whether to remove it now, leave it for a follow-up, or keep it for good (see below). Present the list for review before changing anything.
- [ ] Phase 8 — review the mail code for worst offenders (results below): code that is very far from Tapir's conventions, or badly written or designed in general (e.g. huge view classes, module-level global state, logic in serializers, missing cache parameter on hot paths, untested areas). Present a ranked list with a short reason and a rough effort for each, for review before changing anything. Each item is either fixed in this branch or becomes a follow-up issue.
  - Fixed: bounce classification (`str` vs. `bytes`), configuration description saved as a tuple on create, naive `datetime.now()` when confirming a category registration.
  - Fixed: registration confirmation by `GET`; `GET` now shows a button, `POST` confirms and redirects back (the unused `external/confirmation_registration_complete` route is gone).
  - Done: `tapir/mail/views.py` split into a `views/` package by topic (`email_templates`, `email_configurations`, `dispatches`, `segments`, `triggers`, `mail_categories`, `external`, `ui`), and `tapir/mail/service/` renamed to `services/`.
  - Fixed: public registration form sends at most one confirmation mail per address and category every 15 minutes (cache cooldown), and no longer reveals whether an address is registered.
  - Not decided yet: `str(e)` returned to clients, remaining per-row queries in the dispatch lists (counts and serializer method fields; the version relations are now loaded up front), recipient resolution per row in `MailCategorySerializer`, duplicated create/update logic in `EmailConfigurationVersionViewSet`, DB validation in serializers, module-level registries, untested public flow and viewsets, `alert()` / `any` in the mail UI.
- [ ] Phase 9 — docs: `docs/dev/mail_module.md` (conventions warning, the oddities that remain after phase 7, links to the follow-up issues from phases 5 and 8), `docs/dev/index.md` link, `AGENTS.md`
- [ ] Phase 10 — archive `tapir-mail-module` and `tapir-mail-releases` (after deploy)
- [ ] Phase 11 — delete this plan file (`plans/tapir_mail_integration_plan.md`)

## Decisions

- Tapir is the only user of `tapir-mail`, so the module doesn't need to stay a package.
- Plain copy without git history; the commit message names the source commit of `tapir-mail-module`.
