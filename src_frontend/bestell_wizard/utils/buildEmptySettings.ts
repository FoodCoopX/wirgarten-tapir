import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";

export function buildEmptySettings(): BestellWizardSettings {
  return {
    theme: "biotop",
    pickupLocations: [],
    productTypes: [],
    priceOfAShare: 0,
    allowInvestingMembership: false,
    forceWaitingList: false,
    showCoopContent: false,
    coopStepText: "",
    introStepText: "",
    labelCheckboxSepaMandat: "",
    labelCheckboxContractPolicy: "",
    revocationRightsExplanation: "",
    trialPeriodLengthInWeeks: 0,
    paymentRhythmChoices: {},
    studentStatusAllowed: false,
    introEnabled: false,
  };
}
