import {
  PublicGrowingPeriod,
  PublicProductType,
  PublicWaitingListEntryDetails,
} from "../../api-client";

export function shouldIncludeStepGrowingPeriodChoice(
  selectedProductTypes: PublicProductType[],
  choices: PublicGrowingPeriod[],
  waitingListEntryDetails?: PublicWaitingListEntryDetails,
) {
  if (selectedProductTypes.length === 0) {
    return false;
  }

  if (waitingListEntryDetails !== undefined) {
    return false;
  }

  return choices.length > 1;
}
