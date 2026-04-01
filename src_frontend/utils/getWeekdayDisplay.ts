import dayjs from "dayjs";
import Weekday from "dayjs/plugin/weekday";
import WeekOfYear from "dayjs/plugin/weekOfYear";

export function getWeekdayDisplay(weekday: number) {
  dayjs.extend(Weekday);
  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

  return dayjs().weekday(weekday).format("dddd");
}
