import { PublicProductType } from "../../api-client";
import { getProductById } from "./getProductByIdGlobal.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

export function getTotalPriceForProductType(
  productType: PublicProductType,
  shoppingCart: ShoppingCart,
) {
  let sum = 0;
  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    const product = getProductById(productType, productId);
    if (!product) {
      continue;
    }
    sum += product.price * quantity;
  }
  return sum;
}
