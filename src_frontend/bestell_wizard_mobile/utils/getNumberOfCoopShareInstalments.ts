import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function getNumberOfCoopShareInstalments(
  numberOfCoopShares: number,
  settings: BestellWizardSettings,
) {
  return Math.round(
    (numberOfCoopShares * settings.priceOfAShare) /
      settings.coopShareInstalmentAmount,
  );
}
