import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { isAtLeastOneProductOrdered } from "./isAtLeastOneProductOrdered.ts";
import { PublicProductType } from "../../api-client";
import { isProductInWaitingList } from "./isProductInWaitingList.ts";

export function isWaitingListModeEnabled(
  settings: BestellWizardSettings,
  shoppingCartOrder: ShoppingCart,
  productsTypesInWaitingList: Set<PublicProductType>,
  becomeMemberNow: boolean | null,
) {
  return (
    settings.forceWaitingList ||
    (areAllOrderedProductsInTheWaitingListCart(
      shoppingCartOrder,
      productsTypesInWaitingList,
    ) &&
      becomeMemberNow === false)
  );
}

function areAllOrderedProductsInTheWaitingListCart(
  shoppingCart: ShoppingCart,
  productsTypesInWaitingList: Set<PublicProductType>,
) {
  if (!isAtLeastOneProductOrdered(shoppingCart)) {
    return false;
  }

  for (const [productId, quantity] of Object.entries(
    productsTypesInWaitingList,
  )) {
    if (quantity === 0) continue;

    if (!isProductInWaitingList(productId, productsTypesInWaitingList))
      return false;
  }
  return true;
}
