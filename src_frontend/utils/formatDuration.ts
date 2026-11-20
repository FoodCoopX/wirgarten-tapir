// Formats a duration as "TT HH:MM", e.g. 10080 minutes -> "7 Tage 00:00 Std."
// Computed by hand instead of with the dayjs duration plugin, because dayjs counts
// durations above 30 days in months.
export function formatDuration(totalMinutes: number) {
  const days = Math.floor(totalMinutes / (24 * 60));
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const minutes = totalMinutes % 60;
  const pad = (value: number) => value.toString().padStart(2, "0");
  return `${days} ${days === 1 ? "Tag" : "Tage"} ${pad(hours)}:${pad(minutes)} Std.`;
}
