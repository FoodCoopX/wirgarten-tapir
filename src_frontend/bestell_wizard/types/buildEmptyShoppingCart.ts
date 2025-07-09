import { ShoppingCart } from "./ShoppingCart.ts";
import { PublicProductType } from "../../api-client";

export function buildEmptyShoppingCart(productTypes: PublicProductType[]) {
  const shoppingCart: ShoppingCart = {};
  for (const productType of productTypes) {
    for (const product of productType.products) {
      shoppingCart[product.id!] = 0;
    }
  }
  return shoppingCart;
}
