import { MobileWizardStep } from "../types/MobileWizard.ts";
import { CONTENT_HEIGHT, HEADER_HEIGHT } from "./DIMENSIONS.ts";

export function getStepTopPosition(
  step: MobileWizardStep,
  currentStep: MobileWizardStep,
  steps: MobileWizardStep[],
) {
  if (step === currentStep) {
    return HEADER_HEIGHT + "dvh";
  }

  if (steps.indexOf(step) < steps.indexOf(currentStep)) {
    return -CONTENT_HEIGHT + "dvh";
  }

  return "100dvh";
}
