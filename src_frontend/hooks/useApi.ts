import { useMemo } from "react";
import { Configuration, Middleware } from "../api-client";
import env from "../env.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

// Read on every request: Django rotates the CSRF cookie on login.
const csrfMiddleware: Middleware = {
  pre: async ({ url, init }) => {
    const csrfToken = getCsrfToken();
    if (!csrfToken) return;
    return {
      url,
      init: {
        ...init,
        headers: { ...init.headers, "X-CSRFToken": csrfToken },
      },
    };
  },
};

export function useApi<T>(
  ApiClient: new (configuration: Configuration) => T,
): T {
  return useMemo(
    () =>
      new ApiClient(
        new Configuration({
          basePath: env.REACT_APP_API_ROOT,
          middleware: [csrfMiddleware],
          credentials: "include",
        }),
      ),
    [ApiClient],
  );
}
