import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import { buildFilteredShoppingCart } from "../../bestell_wizard/utils/buildFilteredShoppingCart.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";

export function atLeastOneMonthlyPayment(
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  solidarityContribution: number,
) {
  if (
    isAtLeastOneProductOrdered(
      buildFilteredShoppingCart(shoppingCart, false, productTypesInWaitingList),
    )
  ) {
    return true;
  }
  return solidarityContribution > 0;
}
