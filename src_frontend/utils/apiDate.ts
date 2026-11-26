import dayjs from "dayjs";

// Date-only API fields are "YYYY-MM-DD" strings, read and written in local time.
// Never use new Date("YYYY-MM-DD"): it parses as midnight UTC. See docs/dev/frontend_dates.md.
export function toApiDate(date: Date): string {
  const value = dayjs(date);
  if (!value.isValid()) {
    throw new Error("toApiDate: invalid date");
  }
  return value.format("YYYY-MM-DD");
}

export function fromApiDate(value: string): Date {
  return dayjs(value).toDate();
}
