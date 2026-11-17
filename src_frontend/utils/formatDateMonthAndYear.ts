import { fromApiDate } from "./apiDate.ts";

export function formatDateMonthAndYear(
  date: Date | string | undefined | null,
): string {
  if (!date) {
    return "";
  }

  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: undefined,
  };

  const dateObject = typeof date === "string" ? fromApiDate(date) : date;
  return dateObject.toLocaleDateString("de-DE", options);
}
