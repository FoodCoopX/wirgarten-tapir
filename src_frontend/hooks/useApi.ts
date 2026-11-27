import { useMemo } from "react";
import { Configuration, Middleware } from "../api-client";
import env from "../env.ts";

function getCsrfTokenFromCookie(): string | undefined {
  return document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith("csrftoken="))
    ?.substring("csrftoken=".length);
}

// The CSRF cookie gets rotated on login, so the token rendered into the page can become outdated.
function buildCsrfMiddleware(fallbackCsrfToken: string): Middleware {
  return {
    pre: async ({ url, init }) => ({
      url,
      init: {
        ...init,
        headers: {
          ...init.headers,
          "X-CSRFToken": getCsrfTokenFromCookie() ?? fallbackCsrfToken,
        },
      },
    }),
  };
}

export function useApi<T>(
  ApiClient: new (configuration: Configuration) => T,
  csrfToken: string,
): T {
  return useMemo(
    () =>
      new ApiClient(
        new Configuration({
          basePath: env.REACT_APP_API_ROOT,
          middleware: [buildCsrfMiddleware(csrfToken)],
          credentials: "include",
        }),
      ),
    [ApiClient, csrfToken],
  );
}
