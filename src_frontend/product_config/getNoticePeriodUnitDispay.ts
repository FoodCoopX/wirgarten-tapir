import { NoticePeriodUnitEnum } from "../api-client";

export function getNoticePeriodUnitDisplay(unit: NoticePeriodUnitEnum) {
  switch (unit) {
    case "weeks":
      return "Wochen";
    case "months":
      return "Monate";
  }
}
