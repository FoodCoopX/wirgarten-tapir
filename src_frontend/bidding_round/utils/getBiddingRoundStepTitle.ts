import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Step } from "../../bestell_wizard_mobile/types/Step.ts";

import { BiddingRoundTexts } from "../types/BiddingRoundTypes.ts";
import { getBiddingRoundProductTypeFromStep } from "./getBiddingRoundProductTypeFromStep.ts";

export function getBiddingRoundStepTitle(
  step: Step,
  settings: BestellWizardSettings,
  texts: BiddingRoundTexts,
): string | undefined {
  switch (step) {
    case "bidding_round_intro":
      return texts.introTitle;
    case "bidding_round_pickup_location":
      return texts.pickupLocationTitle;
    case "bidding_round_summary":
      return texts.summaryTitle;
    case "bidding_round_confirmation":
      return settings.strings.step14Title;
    default:
      break;
  }

  const [productType, subStep] = getBiddingRoundProductTypeFromStep(
    step,
    settings,
  );
  if (productType) {
    if (subStep === "intro") {
      return productType.titleBestellwizardIntro || productType.name;
    }
    if (subStep === "bid") {
      return productType.titleBestellwizardProductChoice || productType.name;
    }
  }

  return undefined;
}
