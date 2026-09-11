import dayjs, { Dayjs } from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

/**
 * Pickup location delivery days are stored 0-based (0 = Montag), matching
 * OPTIONS_WEEKDAYS on the backend, while dayjs isoWeekday() is 1-based
 * (1 = Monday). Everything below works off the Monday of the ISO week, so a
 * delivery day is simply that many days later.
 */

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
 * The ISO week-numbering year, which is what the backend stores next to the ISO
 * week. It differs from the calendar year in the days around New Year: asking
 * for the calendar year on 2027-01-01 would query 2027/W53 for rows stored as
 * 2026/W53.
 */
export const currentIsoYear = (): number => dayjs().isoWeekYear();

export const currentIsoWeek = (): number => dayjs().isoWeek();

/**
 * The Monday of an ISO week, anchored on the 4th of January - which is always
 * in ISO week 1 of its own ISO year.
 *
 * Anchoring on today instead would be wrong in the days around New Year: on
 * 2027-01-01, dayjs().year(2027) is still inside ISO year 2026, so asking for
 * week 1 would land in 2026-W01 rather than 2027-W01.
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
 * How many ISO weeks a year has - 52, or 53 in a long year such as 2026.
 *
 * The 28th of December is always in the last ISO week of its own ISO year,
 * which makes it the cheapest way to ask. A fixed 53 would offer a week that
 * does not exist.
 */
export const isoWeeksInYear = (year: number): number =>
  dayjs(`${year}-12-28`).isoWeek();
