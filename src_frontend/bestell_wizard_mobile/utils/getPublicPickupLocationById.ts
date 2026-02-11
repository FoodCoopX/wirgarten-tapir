import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function getPublicPickupLocationById(
  pickupLocationId: string,
  settings: BestellWizardSettings,
) {
  return settings.pickupLocations.find((pl) => pl.id === pickupLocationId);
}