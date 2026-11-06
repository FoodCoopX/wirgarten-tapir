import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Step } from "../../bestell_wizard_mobile/types/Step.ts";
import { getBiddingRoundProductTypeFromStep } from "./getBiddingRoundProductTypeFromStep.ts";

export function getBiddingRoundStepBackground(
  step: Step,
  settings: BestellWizardSettings,
): string | undefined {
  switch (step) {
    case "bidding_round_intro":
      return settings.images.step1BackgroundImage;
    case "bidding_round_pickup_location":
      return settings.images.step5BackgroundImage;
    case "bidding_round_summary":
      return settings.images.step10BackgroundImage;
    case "bidding_round_confirmation":
      return settings.images.step14BackgroundImage;
    default:
      break;
  }

  const [productType] = getBiddingRoundProductTypeFromStep(step, settings);
  if (productType?.backgroundImageInBestellwizard) {
    return productType.backgroundImageInBestellwizard;
  }

  return settings.images.step3BackgroundImage;
}
