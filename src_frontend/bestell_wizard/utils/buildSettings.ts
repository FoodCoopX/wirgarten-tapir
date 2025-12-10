import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { sortProductTypes } from "./sortProductTypes.ts";
import { BestellWizardBaseDataResponse } from "../../api-client";

export function buildSettings(
  baseData: BestellWizardBaseDataResponse,
): BestellWizardSettings {
  baseData.growingPeriodChoices;
  return {
    theme: baseData.theme as TapirTheme,
    pickupLocations: baseData.pickupLocations,
    productTypes: sortProductTypes(baseData.productTypes),
    priceOfAShare: baseData.priceOfAShare,
    allowInvestingMembership: baseData.allowInvestingMembership,
    forceWaitingList: baseData.forceWaitingList,
    showCoopContent: baseData.showCoopContent,
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
    organizationName: baseData.organizationName,
    coopStatuteLink: baseData.coopStatuteLink,
    logoUrl: baseData.logoUrl,
    contactMailAddress: baseData.contactMailAddress,
    distributionChannels: baseData.distributionChannels,
    solidarityContributionChoices: baseData.solidarityContributionChoices,
    solidarityContributionMinimum: baseData.solidarityContributionMinimum,
    solidarityContributionDefault: baseData.solidarityContributionDefault,
    feedbackStepEnabled: baseData.feedbackStepEnabled,
    growingPeriodChoices: baseData.growingPeriodChoices,
    strings: baseData.strings,
    images: baseData.images,
  };
}
