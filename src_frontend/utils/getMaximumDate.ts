// Date-only API strings ("YYYY-MM-DD") compare correctly as strings
export function getMaximumDate(dates: Date[]): Date;
export function getMaximumDate(dates: string[]): string;
export function getMaximumDate(dates: (Date | string)[]): Date | string {
  if (dates.length === 0) {
    throw new Error("getMaximumDate requires at least one date");
  }
  return dates.reduce((a, b) => (a > b ? a : b), dates[0]);
}
