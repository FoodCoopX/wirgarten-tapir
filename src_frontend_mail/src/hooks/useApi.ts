import { Configuration } from "tapir-api-client";
import { getCookie } from "../utils/cookies";

export function useApi<T>(
  ApiClient: new (configuration: Configuration) => T,
): T {
  return new ApiClient(
    new Configuration({
      basePath: "",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      },
    }),
  );
}
