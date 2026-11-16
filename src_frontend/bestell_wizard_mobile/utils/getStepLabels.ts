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

export function getStepName(
  step: string,
  settings: BestellWizardSettings,
): string {
  switch (step) {
    case "1a_welcome":
      return "1A: Willkommen";
    case "1b_welcome_waiting_list":
      return "1B: Willkommen (warteliste)";
    case "2_first_name":
      return "2: Erste Name";
    case "3_product_type_choice":
      return "3: Produkt-Type Auswahl";
    case "3b_growing_period_choice":
      return "3B: Vertragsperiode-Auswahl";
    case "5a_pickup_location_intro":
      return "5A: Verteilstation (Intro)";
    case "5b_pickup_location_choice":
      return "5B: Verteilstation (Auswahl)";
    case "5c_pickup_location_confirm_waiting_list":
      return "5C: Verteilstation (Bestätigung Warteliste)";
    case "6a_coop_intro":
      return "6A: Genossenschaft (Intro)";
    case "6b_association_membership":
      return "6B: Vereinsmitgliedschaft (Auswahl)";
    case "6b_coop_shares":
      return "6B: Genossenschaft (Auswahl)";
    case "6c_coop_member_now":
      return "6C: Genossenschaft (Bestätigung)";
    case "7_solidarity_contribution":
      return "7: Solidarbeitrag";
    case "8_personal_data":
      return "8: Persönliche Daten";
    case "9_banking_data":
      return "9: Bank Daten";
    case "10_summary":
      return "10: Zusammenfassung";
    case "11_legal":
      return "11: Legal";
    case "12_channel":
      return "12: Vertriebskanal";
    case "13_feedback":
      return "13: Feedback";
    case "14_confirmation":
      return "14: Bestätigung";
    case "14b_confirmation_waiting_list":
      return "14: Bestätigung (Warteliste)";
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
