import { ShoppingCart } from "../types/ShoppingCart.ts";

export function isShoppingCartEmpty(shoppingCart: ShoppingCart) {
  const totalQuantityOrdered = Object.values(shoppingCart).reduce(
    (sum, quantity) => sum + quantity,
    0,
  );
  return totalQuantityOrdered === 0;
}
