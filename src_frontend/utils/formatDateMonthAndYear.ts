export function formatDateMonthAndYear(date: Date | undefined | null): string {
  if (!date) {
    return "";
  }

  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: undefined,
  };

  return date.toLocaleDateString("de-DE", options);
}
