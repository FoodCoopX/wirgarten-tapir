// Date-only API strings ("YYYY-MM-DD") compare correctly as strings
export function getMinimumDate(dates: Date[]): Date;
export function getMinimumDate(dates: string[]): string;
export function getMinimumDate(dates: (Date | string)[]): Date | string {
  if (dates.length === 0) {
    throw new Error("getMinimumDate requires at least one date");
  }
  return dates.reduce((a, b) => (a < b ? a : b), dates[0]);
}
