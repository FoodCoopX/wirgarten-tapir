import { PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";

export function isProductTypeOrdered(
  productType: PublicProductType,
  shoppingCart: ShoppingCart,
) {
  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    if (
      productType.products.map((product) => product.id).includes(productId) &&
      quantity > 0
    ) {
      return true;
    }
  }
  return false;
}
