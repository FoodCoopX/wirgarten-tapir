export function formatDate(date: Date | undefined | null): string {
  if (!date) {
    return "";
  }
  return date.toLocaleDateString("de-DE", {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
