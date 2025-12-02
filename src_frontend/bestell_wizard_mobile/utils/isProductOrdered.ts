import { PublicProduct } from "../../api-client";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

export function isProductOrdered(
  product: PublicProduct,
  shoppingCart: ShoppingCart,
) {
  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    if (productId === product.id && quantity > 0) {
      return true;
    }
  }
  return false;
}
