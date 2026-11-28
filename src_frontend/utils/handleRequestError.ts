import React from "react";
import { v4 as uuidv4 } from "uuid";
import { FetchError, ResponseError } from "../api-client";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "./addToast.ts";

// Browsers cancel pending requests when leaving the page, which would show irrelevant errors.
let pageIsUnloading = false;
window.addEventListener("beforeunload", () => {
  pageIsUnloading = true;
  // Only reached if the navigation got cancelled.
  setTimeout(() => (pageIsUnloading = false), 5000);
});
window.addEventListener("pageshow", () => (pageIsUnloading = false));

export function handleRequestError(
  error: unknown,
  errorMessage: string,
  setToastDatas?: React.Dispatch<React.SetStateAction<ToastData[]>>,
): void {
  console.error(error);
  if (error instanceof FetchError && pageIsUnloading) return;
  void showError(error, errorMessage, setToastDatas);
}

async function showError(
  error: unknown,
  errorMessage: string,
  setToastDatas?: React.Dispatch<React.SetStateAction<ToastData[]>>,
) {
  let text = "";
  if (error instanceof ResponseError) {
    text = await error.response.text().catch(() => "");
  }
  const maxLength = 200;
  if (text.length > maxLength) {
    text = text.substring(0, maxLength) + "...";
  }
  if (setToastDatas) {
    addToast(
      {
        title: errorMessage,
        message: text,
        variant: "danger",
        id: uuidv4(),
      },
      setToastDatas,
    );
  } else {
    alert(errorMessage);
  }
}
