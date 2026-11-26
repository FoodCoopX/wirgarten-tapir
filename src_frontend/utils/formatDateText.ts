import { fromApiDate } from "./apiDate.ts";

export function formatDateText(
  date: Date | string | undefined | null,
  includeTime = false,
): string {
  if (!date) {
    return "";
  }

  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  };
  if (includeTime) {
    options.hour = "2-digit";
    options.minute = "2-digit";
  }

  const dateObject = typeof date === "string" ? fromApiDate(date) : date;
  return dateObject.toLocaleDateString("de-DE", options);
}
