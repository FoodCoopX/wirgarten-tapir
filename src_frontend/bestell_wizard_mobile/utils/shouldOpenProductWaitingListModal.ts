import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";
import { isProductOrdered } from "./isProductOrdered.ts";

export function shouldOpenProductWaitingListModal(
  settings: BestellWizardSettings,
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  productTypeIdsOverCapacity: string[],
  productIdsOverCapacity: string[],
  productType: PublicProductType,
) {
  if (!isProductTypeOrdered(productType, shoppingCart)) {
    return false;
  }

  if (productTypesInWaitingList.has(productType)) {
    return false;
  }

  if (settings.forceWaitingList || productType.forceWaitingList) {
    return true;
  }

  if (productTypeIdsOverCapacity.includes(productType.id!)) {
    return true;
  }

  for (const product of productType.products) {
    if (
      isProductOrdered(product, shoppingCart) &&
      productIdsOverCapacity.includes(product.id!)
    ) {
      return true;
    }
  }

  return false;
}
