import { Step } from "../types/Step.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { getProductTypeFromStep } from "./getProductTypeFromStep.ts";

export function getStepBackground(
  step: Step,
  settings: BestellWizardSettings,
): string | undefined {
  switch (step) {
    case "1a_welcome":
    case "1b_welcome":
      return settings.images.step1BackgroundImage;
    case "2_first_name":
      return settings.images.step2BackgroundImage;
    case "3_product_type_choice":
      return settings.images.step3BackgroundImage;
    case "4d_solidarity_contribution":
      return settings.images.step4dBackgroundImage;
    case "5a_pickup_location_intro":
    case "5b_pickup_location_choice":
      return settings.images.step5BackgroundImage;
    case "6a_coop_intro":
    case "6b_coop_shares":
      return settings.images.step6BackgroundImage;
    case "8_personal_data":
      return settings.images.step8BackgroundImage;
    case "9_banking_data":
      return settings.images.step9BackgroundImage;
    case "10_summary":
      return settings.images.step10BackgroundImage;
    case "11_legal":
      return settings.images.step11BackgroundImage;
    case "12_channel":
      return settings.images.step12BackgroundImage;
    case "13_feedback":
      return settings.images.step13BackgroundImage;
    case "14_confirmation":
      return settings.images.step14BackgroundImage;
  }

  const [productType, _] = getProductTypeFromStep(step, settings);
  if (productType) {
    return productType.backgroundImageInBestellwizard;
  }

  return undefined;
}
