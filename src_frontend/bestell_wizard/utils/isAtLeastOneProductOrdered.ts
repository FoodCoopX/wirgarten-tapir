import { ShoppingCart } from "../types/ShoppingCart.ts";

export function isAtLeastOneProductOrdered(shoppingCart: ShoppingCart) {
  return (
    Object.values(shoppingCart).reduce((sum, quantity) => {
      return sum + quantity;
    }, 0) > 0
  );
}
