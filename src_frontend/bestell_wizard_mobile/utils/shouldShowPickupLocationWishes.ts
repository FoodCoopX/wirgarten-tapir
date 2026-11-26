import { PublicPickupLocation } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { wouldTheOrderFitTheProductCapacities } from "./wouldTheOrderFitTheProductCapacities.ts";

export function shouldShowPickupLocationWishes(
  changesDisabled: boolean,
  shoppingCart: ShoppingCart,
  productTypeIdsOverCapacity: string[],
  productIdsOverCapacity: string[],
  settings: BestellWizardSettings,
  selectedPickupLocations: PublicPickupLocation[],
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>,
) {
  if (changesDisabled) {
    return false;
  }

  if (
    !wouldTheOrderFitTheProductCapacities(
      shoppingCart,
      productTypeIdsOverCapacity,
      productIdsOverCapacity,
      settings,
    )
  ) {
    return true;
  }

  switch (selectedPickupLocations.length) {
    case 0:
      return false;
    case 1:
      return pickupLocationsWithCapacityFull.has(selectedPickupLocations[0]);
    default:
      return true;
  }
}
