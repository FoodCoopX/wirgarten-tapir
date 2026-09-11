import React from "react";
import { v4 as uuidv4 } from "uuid";
import { ResponseError } from "../api-client";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "./addToast.ts";

export async function handleRequestError(
  error: unknown,
  errorMessage: string,
  setToastDatas?: React.Dispatch<React.SetStateAction<ToastData[]>>,
) {
  console.error(error);
  // Not every rejection is a ResponseError: a network failure arrives as a
  // FetchError with no .response, and reading it would throw inside this async
  // function and swallow the caller's error. Only a ResponseError carries text
  // meant for a person; anything else is a JS message that would put a stack
  // trace fragment in front of a member. The caller's errorMessage is the
  // toast title either way.
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
