import { fromApiDate } from "./apiDate.ts";

export function formatDateNumeric(
  date: Date | string | undefined | null,
  includeTime = false,
): string {
  if (!date) {
    return "";
  }

  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    // Date-only strings are calendar dates, only times need converting
    timeZone: typeof date === "string" ? undefined : "Europe/Berlin",
  };
  if (includeTime) {
    options.hour = "2-digit";
    options.minute = "2-digit";
  }

  const dateObject = typeof date === "string" ? fromApiDate(date) : date;
  return dateObject.toLocaleDateString("de-DE", options);
}
