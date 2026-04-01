import { Configuration } from "../api-client";
import env from "../env.ts";

export function useApi<T>(
  ApiClient: new (configuration: Configuration) => T,
  csrfToken: string,
): T {
  return new ApiClient(
    new Configuration({
      basePath: env.REACT_APP_API_ROOT,
      headers: { "X-CSRFToken": csrfToken },
      credentials: "include",
    }),
  );
}
