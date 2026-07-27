import {
  PublicGrowingPeriod,
  PublicWaitingListEntryDetails,
} from "../../api-client";

export function shouldIncludeStepGrowingPeriodChoice(
  choices: PublicGrowingPeriod[],
  waitingListEntryDetails?: PublicWaitingListEntryDetails,
) {
  if (waitingListEntryDetails !== undefined) {
    return false;
  }

  return choices.length > 1;
}
