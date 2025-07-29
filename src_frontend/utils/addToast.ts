import { ToastData } from "../types/ToastData.ts";
import React from "react";

export function addToast(
  toastData: ToastData,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
) {
  setToastDatas((datas) => {
    datas.push(toastData);
    return [...datas];
  });
}
