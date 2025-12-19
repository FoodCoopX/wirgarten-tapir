import { Step } from "../types/Step.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function getStepTitle(
  step: Step,
  settings: BestellWizardSettings,
): string | undefined {
  switch (step) {
    case "1a_welcome":
      return settings.strings.step1aTitle;
    case "1b_welcome":
      return settings.strings.step1bTitle;
    case "2_first_name":
      return settings.strings.step2Title;
    case "3_product_type_choice":
      return settings.strings.step3Title;
    case "3b_growing_period_choice":
      return settings.strings.step3bTitle;
    case "5a_pickup_location_intro":
      return settings.strings.step5aTitle;
    case "5b_pickup_location_choice":
      return settings.strings.step5bTitle;
    case "5c_pickup_location_confirm_waiting_list":
      return settings.strings.step5cTitle;
    case "6a_coop_intro":
      return settings.strings.step6aTitle;
    case "6b_coop_shares":
      return settings.strings.step6bTitle;
    case "6c_coop_member_now":
      return settings.strings.step6cTitle;
    case "7_solidarity_contribution":
      return settings.strings.step4dTitle;
    case "8_personal_data":
      return settings.strings.step8Title;
    case "9_banking_data":
      return settings.strings.step9Title;
    case "10_summary":
      return settings.strings.step10Title;
    case "11_legal":
      return settings.strings.step11Title;
    case "12_channel":
      return settings.strings.step12Title;
    case "13_feedback":
      return settings.strings.step13Title;
    case "14_confirmation":
      return settings.strings.step14Title;
    case "14b_confirmation_waiting_list":
      return settings.strings.step14bTitle;
    case "loading":
      return "";
  }

  // If the step is not one of the predefined ones, then it's a product type step
  const separatorIndex = step.lastIndexOf("_");
  const productId = step.slice(0, separatorIndex);
  const productType = settings.productTypes.find(
    (productType) => productType.id === productId,
  );
  if (productType === undefined) {
    return "Fehler: ungültiges Schritt " + step;
  }

  const subStep = step.slice(separatorIndex + 1);
  if (subStep === "intro") {
    return "Unser " + productType.name;
  }
  return productType.titleBestellwizardProductChoice;
}
