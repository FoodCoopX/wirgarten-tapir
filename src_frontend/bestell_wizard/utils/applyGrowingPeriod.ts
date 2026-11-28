import { BestellWizardGrowingPeriodChoice } from "../../api-client";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";

export function applyGrowingPeriod(
  settings: BestellWizardSettings,
  growingPeriod: BestellWizardGrowingPeriodChoice | undefined,
): BestellWizardSettings {
  if (growingPeriod === undefined) {
    return settings;
  }

  return {
    ...settings,
    productTypes: growingPeriod.productTypes,
    pickupLocations: growingPeriod.pickupLocations,
    productTypeIdsThatAreAlreadyAtCapacity:
      growingPeriod.productTypeIdsThatAreAlreadyAtCapacity,
    productIdsThatAreAlreadyAtCapacity:
      growingPeriod.productIdsThatAreAlreadyAtCapacity,
    solidarityContributionMinimum: growingPeriod.solidarityContributionMinimum,
  };
}
