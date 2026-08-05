export function formatDateNumeric(
  date: Date | undefined | null,
  includeTime = false,
): string {
  if (!date) {
    return "";
  }

  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Europe/Berlin",
  };
  if (includeTime) {
    options.hour = "2-digit";
    options.minute = "2-digit";
  }

  console.log(date);
  return date.toLocaleDateString("de-DE", options);
}
