import { ResponseError } from "../api-client";
import { ToastData } from "../types/ToastData.ts";
import { v4 as uuidv4 } from "uuid";
import React from "react";
import { addToast } from "./addToast.ts";

export async function handleRequestError(
  error: ResponseError,
  errorMessage?: string,
  setToastDatas?: React.Dispatch<React.SetStateAction<ToastData[]>>,
) {
  if (!errorMessage) {
    errorMessage = error.message;
  }
  console.error(error);
  if (setToastDatas) {
    addToast(
      {
        title: errorMessage ?? "Fehler!",
        message: await error.response.text(),
        variant: "danger",
        id: uuidv4(),
      },
      setToastDatas,
    );
  } else {
    alert(errorMessage);
  }
}
