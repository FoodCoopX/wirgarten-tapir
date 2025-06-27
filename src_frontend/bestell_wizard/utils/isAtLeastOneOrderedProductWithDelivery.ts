import { ShoppingCart } from "../types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";

export function isAtLeastOneOrderedProductWithDelivery(
  shoppingCart: ShoppingCart,
  productTypes: PublicProductType[],
) {
  const orderedProductIds = Object.keys(shoppingCart);
  for (const orderedProductId of orderedProductIds) {
    if (shoppingCart[orderedProductId] === 0) {
      continue;
    }
    for (const productType of productTypes) {
      if (productType.noDelivery) {
        continue;
      }
      for (const product of productType.products) {
        if (product.id === orderedProductId) {
          console.log(orderedProductId);
          console.log(productType);
          console.log(shoppingCart);
          return true;
        }
      }
    }
  }
  return false;
}
