import { shouldShowWarningProductTypeNotAvailable } from "../../utils/shouldShowWarningNotAvailable.ts";
import { PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

export function shouldShowWarningCurrentOrderIsOverCapacity(
  productType: PublicProductType,
  settings: BestellWizardSettings,
  productTypeIdsOverCapacity: string[],
  productIdsOverCapacity: string[],
  shoppingCart: ShoppingCart,
) {
  if (shouldShowWarningProductTypeNotAvailable(productType, settings)) {
    return false;
  }

  if (productTypeIdsOverCapacity.includes(productType.id!)) {
    return true;
  }

  for (const product of productType.products) {
    if (!Object.keys(shoppingCart).includes(product.id!)) {
      continue;
    }

    if (shoppingCart[product.id!] === 0) {
      continue;
    }

    if (productIdsOverCapacity.includes(product.id!)) {
      return true;
    }
  }

  return false;
}
