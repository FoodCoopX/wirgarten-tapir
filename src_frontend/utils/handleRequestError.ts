import { ResponseError } from "../api-client";
import { ToastData } from "../types/ToastData.ts";
import { v4 as uuidv4 } from "uuid";
import React from "react";
import { addToast } from "./addToast.ts";

export async function handleRequestError(
  error: ResponseError,
  errorMessage: string,
  setToastDatas?: React.Dispatch<React.SetStateAction<ToastData[]>>,
) {
  console.error(error);
  let text = await error.response.text();
  if (text.length > 100) {
    text = text.substring(0, 100) + "...";
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
