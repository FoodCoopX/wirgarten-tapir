import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { isAtLeastOneProductOrdered } from "./isAtLeastOneProductOrdered.ts";

export function isWaitingListModeEnabled(
  settings: BestellWizardSettings,
  shoppingCartOrder: ShoppingCart,
  shoppingCartWaitingList: ShoppingCart,
  becomeMemberNow: boolean | null,
) {
  return (
    settings.forceWaitingList ||
    (areAllOrderedProductsInTheWaitingListCart(
      shoppingCartOrder,
      shoppingCartWaitingList,
    ) &&
      becomeMemberNow === false)
  );
}

function areAllOrderedProductsInTheWaitingListCart(
  shoppingCartOrder: ShoppingCart,
  shoppingCartWaitingList: ShoppingCart,
) {
  return (
    !isAtLeastOneProductOrdered(shoppingCartOrder) &&
    isAtLeastOneProductOrdered(shoppingCartWaitingList)
  );
}
