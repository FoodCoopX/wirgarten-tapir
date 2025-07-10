import { ResponseError } from "../api-client";
import { ToastData } from "../types/ToastData.ts";
import { v4 as uuidv4 } from "uuid";

export async function handleRequestError(
  error: ResponseError,
  errorMessage?: string,
  addToast?: (data: ToastData) => void,
) {
  if (!errorMessage) {
    errorMessage = error.message;
  }
  console.error(error);
  if (addToast) {
    addToast({
      title: errorMessage ?? "Fehler!",
      message: await error.response.text(),
      variant: "danger",
      id: uuidv4(),
    });
  } else {
    alert(errorMessage);
  }
}
