import { BestellWizardBaseDataResponse } from "../../api-client";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { applyGrowingPeriod } from "./applyGrowingPeriod.ts";

export function buildSettings(
  baseData: BestellWizardBaseDataResponse,
): BestellWizardSettings {
  const settings: BestellWizardSettings = {
    theme: baseData.theme as TapirTheme,
    pickupLocations: [],
    productTypes: [],
    associationMembershipTypes: baseData.associationMembershipTypes,
    priceOfAShare: baseData.priceOfAShare,
    coopMinShares: baseData.coopMinShares,
    coopShareInstalmentsEnabled: baseData.coopShareInstalmentsEnabled,
    coopShareInstalmentAmount: baseData.coopShareInstalmentAmount,
    allowInvestingMembership: baseData.allowInvestingMembership,
    associationsAllowInvestingMembership:
      baseData.associationsAllowInvestingMembership,
    forceWaitingList: baseData.forceWaitingList,
    showCoopContent: baseData.showCoopContent,
    labelCheckboxSepaMandat: baseData.labelCheckboxSepaMandat,
    explanationCheckboxSepaMandat: baseData.explanationCheckboxSepaMandat,
    labelCheckboxContractPolicy: baseData.labelCheckboxContractPolicy,
    explanationCheckboxContractPolicy: baseData.explanationCheckboxContractPolicy,
    trialPeriodLengthInWeeks: baseData.trialPeriodLengthInWeeks,
    paymentRhythmChoices: baseData.paymentRhythmChoices,
    studentStatusAllowed: baseData.studentStatusAllowed,
    phoneNumberRequired: baseData.phoneNumberRequired,
    pseudonymEnabled: baseData.pseudonymEnabled,
    introEnabled: baseData.introEnabled,
    productTypeIdsThatAreAlreadyAtCapacity: [],
    productIdsThatAreAlreadyAtCapacity: [],
    organizationName: baseData.organizationName,
    coopStatuteLink: baseData.coopStatuteLink,
    logoUrl: baseData.logoUrl,
    contactMailAddress: baseData.contactMailAddress,
    websiteUrl: baseData.websiteUrl,
    distributionChannels: baseData.distributionChannels,
    solidarityContributionChoices: baseData.solidarityContributionChoices,
    solidarityContributionMinimum: null,
    solidarityContributionDefault: baseData.solidarityContributionDefault,
    feedbackStepEnabled: baseData.feedbackStepEnabled,
    growingPeriodChoices: baseData.growingPeriodChoices,
    solidarityStepPosition: baseData.solidarityStepPosition,
    legalStatus: baseData.legalStatus,
    strings: baseData.strings,
    images: baseData.images,
    debug: baseData.debug,
  };

  return applyGrowingPeriod(settings, baseData.growingPeriodChoices[0]);
}
