export function getMaximumDate(dates: Date[]): Date {
  if (dates.length === 0) {
    throw new Error("getMaximumDate requires at least one date");
  }
  return dates.reduce((a, b) => (a > b ? a : b), dates[0]);
}
