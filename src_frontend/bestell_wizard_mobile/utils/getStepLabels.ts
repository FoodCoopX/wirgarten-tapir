import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Phase } from "../types/Phase.ts";

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

const STEP_NAMES: Record<string, string> = {
  "1a_welcome": "1A: Willkommen",
  "1b_welcome_waiting_list": "1B: Willkommen (warteliste)",
  "2_first_name": "2: Erste Name",
  "3_product_type_choice": "3: Produkt-Type Auswahl",
  "3b_growing_period_choice": "3B: Vertragsperiode-Auswahl",
  "5a_pickup_location_intro": "5A: Verteilstation (Intro)",
  "5b_pickup_location_choice": "5B: Verteilstation (Auswahl)",
  "5c_pickup_location_confirm_waiting_list":
    "5C: Verteilstation (Bestätigung Warteliste)",
  "6a_coop_intro": "6A: Genossenschaft (Intro)",
  "6b_association_membership": "6B: Vereinsmitgliedschaft (Auswahl)",
  "6b_coop_shares": "6B: Genossenschaft (Auswahl)",
  "6c_coop_member_now": "6C: Genossenschaft (Bestätigung)",
  "7_solidarity_contribution": "7: Solidarbeitrag",
  "8_personal_data": "8: Persönliche Daten",
  "9_banking_data": "9: Bank Daten",
  "10_summary": "10: Zusammenfassung",
  "11_legal": "11: Legal",
  "12_channel": "12: Vertriebskanal",
  "13_feedback": "13: Feedback",
  "14_confirmation": "14: Bestätigung",
  "14b_confirmation_waiting_list": "14: Bestätigung (Warteliste)",
};

export function getStepName(
  step: string,
  settings: BestellWizardSettings,
): string {
  const stepName = STEP_NAMES[step];
  if (stepName !== undefined) {
    return stepName;
  }
  for (const productType of settings.productTypes) {
    if (!step.includes(productType.id!)) {
      continue;
    }
    if (step.includes("intro")) {
      return "4A: " + productType.name + " (Intro)";
    }
    if (step.includes("order")) {
      return "4B: " + productType.name + " (Bestellung)";
    }
    step = step.replace(productType.id!, productType.name);
  }
  return step;
}
