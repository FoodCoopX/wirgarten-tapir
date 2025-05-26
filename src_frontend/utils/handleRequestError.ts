import { ResponseError } from "../api-client";

export async function handleRequestError(error: ResponseError) {
  console.error(error);
  alert(await error.response.text());
}
