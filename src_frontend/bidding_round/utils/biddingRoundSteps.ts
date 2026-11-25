import { PublicProductType, RoundTexts } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import {
  MobileWizardPhase,
  MobileWizardStep,
} from "../../components/mobile_wizard/types/MobileWizard.ts";

interface BuildBiddingRoundStepsParams {
  hasActiveRound: boolean;
  isAuthenticated: boolean;
  productTypeId?: string | null;
  hasProductIntro: boolean;
  sepaEnabled: boolean;
  feedbackEnabled: boolean;
}

export function buildBiddingRoundSteps({
  hasActiveRound,
  isAuthenticated,
  productTypeId,
  hasProductIntro,
  sepaEnabled,
  feedbackEnabled,
}: BuildBiddingRoundStepsParams): MobileWizardStep[] {
  if (!hasActiveRound || !isAuthenticated || !productTypeId) {
    return ["bidding_round_intro"];
  }

  const steps = ["bidding_round_intro"];
  if (hasProductIntro) {
    steps.push(productTypeId + "_intro");
  }
  steps.push(productTypeId + "_bid");
  if (sepaEnabled) {
    steps.push("bidding_round_sepa");
  }
  steps.push("bidding_round_privacy");
  if (feedbackEnabled) {
    steps.push("bidding_round_feedback");
  }
  steps.push("bidding_round_summary");
  steps.push("bidding_round_confirmation");
  return steps;
}

export function getProductTypeFromStep(
  step: MobileWizardStep,
  settings: BestellWizardSettings,
): PublicProductType | undefined {
  const separatorIndex = step.lastIndexOf("_");
  if (separatorIndex === -1) {
    return undefined;
  }
  const productTypeId = step.slice(0, separatorIndex);
  return settings.productTypes.find(
    (productType) => productType.id === productTypeId,
  );
}

export function getBiddingRoundPhase(
  step: MobileWizardStep,
): MobileWizardPhase {
  switch (step) {
    case "bidding_round_intro":
      return "intro";
    case "bidding_round_sepa":
    case "bidding_round_privacy":
    case "bidding_round_feedback":
      return "personal_data";
    case "bidding_round_confirmation":
      return "confirmation";
  }
  return "bid";
}

export function getBiddingRoundPhaseLabel(phase: MobileWizardPhase): string {
  switch (phase) {
    case "intro":
      return "Intro";
    case "personal_data":
      return "Persönliche Daten";
    case "confirmation":
      return "Bestätigung";
  }
  return "Gebot";
}

export function getBiddingRoundStepTitle(
  step: MobileWizardStep,
  settings: BestellWizardSettings,
  texts: RoundTexts,
): string | undefined {
  switch (step) {
    case "bidding_round_intro":
      return texts.introTitle;
    case "bidding_round_sepa":
      return "SEPA-Lastschrift";
    case "bidding_round_privacy":
      return texts.privacyTitle;
    case "bidding_round_feedback":
      return settings.strings?.step13Title;
    case "bidding_round_summary":
      return texts.summaryTitle;
    case "bidding_round_confirmation":
      return settings.strings?.step14Title || "Danke";
  }

  const productType = getProductTypeFromStep(step, settings);
  if (!productType) {
    return undefined;
  }
  if (step.endsWith("_intro")) {
    return productType.titleBestellwizardIntro || productType.name;
  }
  return productType.name + " & Gebot";
}

export function getBiddingRoundStepBackground(
  step: MobileWizardStep,
  settings: BestellWizardSettings,
): string | undefined {
  switch (step) {
    case "bidding_round_intro":
      return settings.images?.step1BackgroundImage;
    case "bidding_round_sepa":
      return settings.images?.step9BackgroundImage;
    case "bidding_round_privacy":
      return settings.images?.step11BackgroundImage;
    case "bidding_round_feedback":
      return settings.images?.step13BackgroundImage;
    case "bidding_round_summary":
      return settings.images?.step10BackgroundImage;
    case "bidding_round_confirmation":
      return settings.images?.step14BackgroundImage;
  }

  return getProductTypeFromStep(step, settings)?.backgroundImageInBestellwizard;
}

export function getBiddingRoundStepName(
  step: MobileWizardStep,
  settings: BestellWizardSettings,
): string {
  switch (step) {
    case "bidding_round_intro":
      return "Intro";
    case "bidding_round_sepa":
      return "SEPA";
    case "bidding_round_privacy":
      return "Datenschutz";
    case "bidding_round_feedback":
      return "Feedback";
    case "bidding_round_summary":
      return "Zusammenfassung";
    case "bidding_round_confirmation":
      return "Bestätigung";
  }

  const productType = getProductTypeFromStep(step, settings);
  if (!productType) {
    return step;
  }
  if (step.endsWith("_intro")) {
    return productType.name + " (Intro)";
  }
  return productType.name + " (Gebot)";
}
