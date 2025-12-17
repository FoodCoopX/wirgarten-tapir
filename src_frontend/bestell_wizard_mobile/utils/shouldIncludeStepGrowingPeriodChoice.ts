import { PublicGrowingPeriod, PublicProductType } from "../../api-client";
import dayjs from "dayjs";

export function shouldIncludeStepGrowingPeriodChoice(
  selectedProductTypes: PublicProductType[],
  choices: PublicGrowingPeriod[],
) {
  if (selectedProductTypes.length === 0) {
    return false;
  }

  if (choices.length > 1) {
    return true;
  }

  if (choices.length === 1) {
    const period = choices[0];
    return dayjs().add(31, "days").isBefore(dayjs(period.startDate));
  }

  return false;
}
