import { Step } from "../types/Step.ts";
import { Phase } from "../types/Phase.ts";

export function getPhase(step: Step): Phase {
  switch (step) {
    case "loading":
      return "loading";
    case "1a_welcome":
    case "1b_welcome_waiting_list":
    case "2_first_name":
    case "3_product_type_choice":
      return "intro";
    case "7_solidarity_contribution":
      return "solidarity";
    case "5a_pickup_location_intro":
    case "5b_pickup_location_choice":
      return "pickup_location";
    case "6a_coop_intro":
    case "6b_coop_shares":
    case "6c_coop_member_now":
      return "coop";
    case "8_personal_data":
    case "9_banking_data":
    case "10_summary":
    case "11_legal":
      return "personal_data";
    case "12_channel":
    case "13_feedback":
      return "feedback";
    case "14_confirmation":
      return "confirmation";

    default:
      const separatorIndex = step.lastIndexOf("_");
      if (separatorIndex == -1) {
        alert("Missing phase for step " + step);
        return "unknown";
      }
      return step.slice(0, separatorIndex);
  }
}
