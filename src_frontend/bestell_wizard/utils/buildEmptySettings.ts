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
    productTypeIdsThatAreAlreadyAtCapacity: [],
    productIdsThatAreAlreadyAtCapacity: [],
    organizationName: "",
    coopStatuteLink: "",
    logoUrl: "",
    strings: {
      step1aTitle: "",
      step1aText: "",
      step1bTitle: "",
      step1bText: "",
      step2Title: "",
      step2Text: "",
    },
  };
}
