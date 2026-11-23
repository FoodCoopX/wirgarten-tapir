import {
  BestellWizardGrowingPeriodChoice,
  PublicWaitingListEntryDetails,
} from "../../api-client";

export function shouldIncludeStepGrowingPeriodChoice(
  choices: BestellWizardGrowingPeriodChoice[],
  waitingListEntryDetails?: PublicWaitingListEntryDetails,
) {
  if (waitingListEntryDetails !== undefined) {
    return false;
  }

  return choices.length > 1;
}
