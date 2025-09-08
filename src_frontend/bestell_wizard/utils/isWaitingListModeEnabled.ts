import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";

export function isWaitingListModeEnabled(
  settings: BestellWizardSettings,
  shoppingCartOrder: ShoppingCart,
  shoppingCartWaitingList: ShoppingCart,
) {
  return (
    settings.forceWaitingList ||
    areAllOrderedProductsInTheWaitingListCart(
      shoppingCartOrder,
      shoppingCartWaitingList,
    )
  );
}

function areAllOrderedProductsInTheWaitingListCart(
  shoppingCartOrder: ShoppingCart,
  shoppingCartWaitingList: ShoppingCart,
) {
  const quantityInWaitingListCart = Object.values(
    shoppingCartWaitingList,
  ).reduce((sum, quantity) => {
    return sum + quantity;
  }, 0);
  return (
    Object.keys(shoppingCartOrder).length === 0 && quantityInWaitingListCart > 0
  );
}
