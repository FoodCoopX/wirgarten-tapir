import { Step } from "../../bestell_wizard_mobile/types/Step.ts";

interface BuildBiddingRoundStepsParams {
  isAuthenticated: boolean;
  activeProductTypeId?: string;
  pickupLocationsEnabled: boolean;
}

export function buildBiddingRoundSteps({
  isAuthenticated,
  activeProductTypeId,
  pickupLocationsEnabled,
}: BuildBiddingRoundStepsParams): Step[] {
  const steps: Step[] = ["bidding_round_intro"];

  if (isAuthenticated) {
    if (activeProductTypeId) {
      steps.push(activeProductTypeId + "_intro", activeProductTypeId + "_bid");
    }

    if (pickupLocationsEnabled) {
      steps.push("bidding_round_pickup_location");
    }

    steps.push("bidding_round_summary");
  }

  steps.push("bidding_round_confirmation");
  return steps;
}
