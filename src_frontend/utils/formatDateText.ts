export function formatDateText(
  date: Date | undefined | null,
  includeTime = false,
): string {
  if (!date) {
    return "";
  }

  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: "numeric",
  };
  if (includeTime) {
    options.hour = "2-digit";
    options.minute = "2-digit";
  }

  return date.toLocaleDateString("de-DE", options);
}
