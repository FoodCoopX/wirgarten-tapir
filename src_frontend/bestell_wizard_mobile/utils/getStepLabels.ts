import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Phase } from "../types/Phase.ts";
import { Step } from "../types/Step.ts";

export function getPhaseLabel(
  phase: Phase,
  settings: BestellWizardSettings,
): string {
  switch (phase) {
    case "intro":
      return "Intro";
    case "coop":
      if (settings.legalStatus === "coop") return "Genossenschaft";
      else return "Verein";
    case "pickup_location":
      return "Verteilstation";
    case "solidarity":
      return "Solibeitrag";
    case "personal_data":
      return "Persönliche Daten";
    case "feedback":
      return "Feedback";
    case "confirmation":
      return "Bestätigung";
  }

  for (const productType of settings.productTypes) {
    if (productType.id === phase) {
      return productType.name;
    }
  }

  return phase;
}

const STEP_NAMES = {
  "1a_welcome": "1A: Willkommen",
  "1b_welcome_waiting_list": "1B: Willkommen (warteliste)",
  "2_first_name": "2: Erste Name",
  "3_product_type_choice": "3: Produkt-Type Auswahl",
  "3b_growing_period_choice": "3B: Vertragsperiode-Auswahl",
  "5a_pickup_location_intro": "5A: Verteilstation (Intro)",
  "5b_delivery_mode_choice": "5B: Abholung oder Hauslieferung",
  "5c_pickup_location_choice": "5C: Verteilstation (Auswahl)",
  "5d_home_delivery_choice": "5D: Hauslieferung (Auswahl)",
  "5e_pickup_location_confirm_waiting_list":
    "5E: Verteilstation (Bestätigung Warteliste)",
  "6a_coop_intro": "6A: Genossenschaft (Intro)",
  "6b_association_membership": "6B: Vereinsmitgliedschaft (Auswahl)",
  "6b_coop_shares": "6B: Genossenschaft (Auswahl)",
  "6c_coop_member_now": "6C: Genossenschaft (Bestätigung)",
  "7_solidarity_contribution": "7: Solidarbeitrag",
  "8_personal_data": "8: Persönliche Daten",
  "8b_delivery_address": "8B: Lieferadresse",
  "9_banking_data": "9: Bank Daten",
  "10_summary": "10: Zusammenfassung",
  "11_legal": "11: Legal",
  "12_channel": "12: Vertriebskanal",
  "13_feedback": "13: Feedback",
  "14_confirmation": "14: Bestätigung",
  "14b_confirmation_waiting_list": "14: Bestätigung (Warteliste)",
  loading: "Laden",
} satisfies Record<Step, string>;

const stepNames: Record<string, string | undefined> = STEP_NAMES;

export function getStepName(
  step: Step,
  settings: BestellWizardSettings,
): string {
  const stepName = stepNames[step];
  if (stepName !== undefined) {
    return stepName;
  }

  let remainingStep: string = step;
  for (const productType of settings.productTypes) {
    if (!remainingStep.includes(productType.id!)) {
      continue;
    }
    if (remainingStep.includes("intro")) {
      return "4A: " + productType.name + " (Intro)";
    }
    if (remainingStep.includes("order")) {
      return "4B: " + productType.name + " (Bestellung)";
    }
    remainingStep = remainingStep.replace(productType.id!, productType.name);
  }
  return remainingStep;
}
