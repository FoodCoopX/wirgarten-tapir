import { ShoppingCart } from "../types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";
import { isProductInWaitingList } from "./isProductInWaitingList.ts";

export function buildFilteredShoppingCart(
  shoppingCart: ShoppingCart,
  inWaitingList: boolean,
  productsTypesInWaitingList: Set<PublicProductType>,
) {
  const filteredCart: ShoppingCart = {};
  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    if (quantity === 0) continue;

    if (
      inWaitingList ===
      isProductInWaitingList(productId, productsTypesInWaitingList)
    ) {
      filteredCart[productId] = quantity;
    }
  }

  return filteredCart;
}
