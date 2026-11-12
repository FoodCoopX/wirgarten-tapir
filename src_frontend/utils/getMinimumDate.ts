export function getMinimumDate(dates: Date[]): Date {
  if (dates.length === 0) {
    throw new Error("getMinimumDate requires at least one date");
  }
  return dates.reduce((a, b) => (a < b ? a : b), dates[0]);
}
