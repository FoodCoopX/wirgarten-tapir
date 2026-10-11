---
applyTo: "src_frontend/**/*.{ts,tsx}"
---

# Frontend rules (React islands)

Details: [doc/dev/frontend.md](../../doc/dev/frontend.md).

- React islands, not an SPA. A feature needs all four of: `src_frontend/<feature>/<feature>_entry.tsx`, an entry in
  `rollupOptions.input` in `vite.config.ts`, `{% vite_asset %}` in the Django template, and a mount `<div id="...">`
  with `{% csrf_token %}` plus `{% javascript_environment_variables %}`. Missing any one fails silently.
- Entry pattern: `document.getElementById(...)` → `createRoot(node).render(<X ... />)`, with an `else { console.error }`.
  Data comes from `node.dataset.*` (always strings) and the CSRF token from `getCsrfToken()`, passed down as a prop.
- All API calls go through `useApi(ApiClient, csrfToken)` from `src_frontend/hooks/useApi.ts`. Never call `fetch()`
  directly — it loses the CSRF header and cookies.
- `src_frontend/api-client/` and `schema.yml` are **generated**; never hand-edit. After any DRF change, run
  `generate_api_schema.sh` then `generate_api_clients.sh` and commit the result.
- State: React hooks only (no Redux/Zustand/React Query). Keep the `isLoading` / `error` / data triple that existing
  components use.
- No path aliases: relative imports with explicit `.ts`/`.tsx` extensions.
- Reuse `src_frontend/components/` (`TapirButton`, `TapirDateInput`, `ConfirmModal`, `EmailInput`, pagination) before
  writing new widgets; UI is react-bootstrap / Bootstrap 5.
- Dates via `dayjs` with German locale; API values are ISO-8601 and date-only fields parse as UTC midnight — do not
  format them naively or they shift by a day.
- User-facing strings are German; code and comments English. TypeScript is `strict`.
- Format with Prettier (organize-imports plugin). Never render untrusted HTML (`dangerouslySetInnerHTML` is not used).
