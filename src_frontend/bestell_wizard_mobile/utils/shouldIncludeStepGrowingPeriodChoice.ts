import { PublicGrowingPeriod, PublicProductType } from "../../api-client";

export function shouldIncludeStepGrowingPeriodChoice(
  selectedProductTypes: PublicProductType[],
  choices: PublicGrowingPeriod[],
) {
  if (selectedProductTypes.length === 0) {
    return false;
  }

  return choices.length > 1;
}
