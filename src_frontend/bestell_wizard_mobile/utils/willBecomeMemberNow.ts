import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function willBecomeMemberNow(
  settings: BestellWizardSettings,
  becomeMemberNow: boolean | null,
) {
  return !settings.forceWaitingList && becomeMemberNow !== false;
}
