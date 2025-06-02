import { ResponseError } from "../api-client";

export async function handleRequestError(
  error: ResponseError,
  errorMessage?: string,
) {
  if (!errorMessage) {
    errorMessage = error.message;
  }
  console.error(error);
  alert(errorMessage);
}
