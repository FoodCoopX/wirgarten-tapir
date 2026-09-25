import dayjs, { Dayjs } from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

// Delivery days are stored 0-based (0 = Montag) to match OPTIONS_WEEKDAYS on
// the backend, while dayjs isoWeekday() is 1-based.

export const DAY_LABELS: Record<number, string> = {
  0: "Montag",
  1: "Dienstag",
  2: "Mittwoch",
  3: "Donnerstag",
  4: "Freitag",
  5: "Samstag",
  6: "Sonntag",
};

/**
 * The ISO week-numbering year, which is what the backend stores next to the
 * week. It differs from the calendar year in the days around New Year.
 */
export const currentIsoYear = (): number => dayjs().isoWeekYear();

export const currentIsoWeek = (): number => dayjs().isoWeek();

/**
 * The Monday of an ISO week, anchored on the 4th of January - which is always
 * in ISO week 1 of its own ISO year.
 */
const isoWeekStart = (year: number, week: number): Dayjs =>
  dayjs(`${year}-01-04`)
    .startOf("isoWeek")
    .add(week - 1, "week");

/** The date of a 0-based delivery day within the given ISO year and week. */
export const deliveryDate = (
  year: number,
  week: number,
  deliveryDay: number,
): Dayjs => isoWeekStart(year, week).add(deliveryDay, "day");

export const formatDeliveryDate = (
  year: number,
  week: number,
  deliveryDay: number,
): string => deliveryDate(year, week, deliveryDay).format("DD.MM.YYYY");

/**
 * How many ISO weeks a year has - 52, or 53 in a long year. The 28th of
 * December is always in the last ISO week of its own ISO year.
 */
export const isoWeeksInYear = (year: number): number =>
  dayjs(`${year}-12-28`).isoWeek();
