import { Step } from "../../bestell_wizard_mobile/types/Step.ts";

interface BuildBiddingRoundStepsParams {
  isAuthenticated: boolean;
  activeProductTypeId?: string;
  pickupLocationsEnabled: boolean;
  skipIntro?: boolean;
  skipProductDescription?: boolean;
}

export function buildBiddingRoundSteps({
  isAuthenticated,
  activeProductTypeId,
  pickupLocationsEnabled,
  skipIntro,
  skipProductDescription,
}: BuildBiddingRoundStepsParams): Step[] {
  const steps: Step[] = [];

  // The intro carries the login for anonymous visitors, so it can only be skipped
  // once the member is authenticated.
  const introSkipped = Boolean(skipIntro) && isAuthenticated;
  if (!introSkipped) {
    steps.push("bidding_round_intro");
  }

  if (isAuthenticated) {
    if (activeProductTypeId && !skipProductDescription) {
      steps.push(activeProductTypeId + "_intro");
    }
    if (activeProductTypeId) {
      steps.push(activeProductTypeId + "_bid");
    }

    if (pickupLocationsEnabled) {
      steps.push("bidding_round_pickup_location");
    }

    steps.push("bidding_round_summary");
  }

  steps.push("bidding_round_confirmation");
  return steps;
}
