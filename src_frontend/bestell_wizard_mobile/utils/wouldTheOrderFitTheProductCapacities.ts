import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { getProductTypeByProductId } from "./getProductTypeByProductId.ts";

export function wouldTheOrderFitTheProductCapacities(
  shoppingCart: ShoppingCart,
  productTypeIdsOverCapacity: string[],
  productIdsOverCapacity: string[],
  settings: BestellWizardSettings,
) {
  for (const productId of Object.keys(shoppingCart)) {
    if (productIdsOverCapacity.includes(productId)) {
      return false;
    }

    const productType = getProductTypeByProductId(productId, settings);
    if (productTypeIdsOverCapacity.includes(productType!.id!)) {
      return false;
    }
  }

  return true;
}
