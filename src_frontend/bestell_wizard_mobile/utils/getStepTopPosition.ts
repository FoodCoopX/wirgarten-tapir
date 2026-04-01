import { Step } from "../types/Step.ts";
import { CONTENT_HEIGHT, HEADER_HEIGHT } from "./DIMENSIONS.ts";

export function getStepTopPosition(
  step: Step,
  currentStep: Step,
  steps: Step[],
) {
  if (step === currentStep) {
    return HEADER_HEIGHT + "dvh";
  }

  if (steps.indexOf(step) < steps.indexOf(currentStep)) {
    return -CONTENT_HEIGHT + "dvh";
  }

  return "100dvh";
}
