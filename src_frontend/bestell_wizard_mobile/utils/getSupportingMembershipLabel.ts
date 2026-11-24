import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function getSupportingMembershipLabel(
  settings: BestellWizardSettings,
): string {
  if (settings.legalStatus === "association") {
    const names = settings.associationMembershipTypes
      .filter((type) => type.isSupportingMembership)
      .map((type) => type.name);

    if (names.length > 0) {
      return names.join(", ");
    }
  }

  return settings.strings.step3SupportingMembershipName;
}
