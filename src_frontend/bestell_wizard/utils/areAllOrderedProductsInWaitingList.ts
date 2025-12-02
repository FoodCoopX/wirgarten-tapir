import { ShoppingCart } from "../types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";
import { isProductInWaitingList } from "./isProductInWaitingList.ts";
import { isAtLeastOneProductOrdered } from "./isAtLeastOneProductOrdered.ts";

export function areAllOrderedProductsInWaitingList(
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
) {
  if (!isAtLeastOneProductOrdered(shoppingCart)) {
    return false;
  }

  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    if (quantity === 0) continue;

    if (!isProductInWaitingList(productId, productTypesInWaitingList))
      return false;
  }
  return true;
}
