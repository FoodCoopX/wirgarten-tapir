import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { sortProductTypes } from "./sortProductTypes.ts";
import {
  BestellWizardBaseDataResponse,
  PublicPickupLocation,
} from "../../api-client";

export function buildSettings(
  baseData: BestellWizardBaseDataResponse,
  pickupLocations: PublicPickupLocation[],
): BestellWizardSettings {
  return {
    theme: baseData.theme as TapirTheme,
    pickupLocations: pickupLocations,
    productTypes: sortProductTypes(baseData.productTypes),
    priceOfAShare: baseData.priceOfAShare,
    allowInvestingMembership: baseData.allowInvestingMembership,
    forceWaitingList: baseData.forceWaitingList,
    showCoopContent: baseData.showCoopContent,
    coopStepText: baseData.coopStepText,
    introStepText: baseData.introStepText,
    labelCheckboxSepaMandat: baseData.labelCheckboxSepaMandat,
    labelCheckboxContractPolicy: baseData.labelCheckboxContractPolicy,
    revocationRightsExplanation: baseData.revocationRightsExplanation,
    trialPeriodLengthInWeeks: baseData.trialPeriodLengthInWeeks,
    paymentRhythmChoices: baseData.paymentRhythmChoices,
    studentStatusAllowed: baseData.studentStatusAllowed,
    introEnabled: baseData.introEnabled,
    productTypeIdsThatAreAlreadyAtCapacity:
      baseData.productTypeIdsThatAreAlreadyAtCapacity,
    productIdsThatAreAlreadyAtCapacity:
      baseData.productIdsThatAreAlreadyAtCapacity,
  };
}
