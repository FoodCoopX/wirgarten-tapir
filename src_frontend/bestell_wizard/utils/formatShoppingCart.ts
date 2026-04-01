import { ShoppingCart } from "../types/ShoppingCart.ts";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";

export function formatShoppingCart(
  shoppingCart: ShoppingCart,
  settings: BestellWizardSettings,
): string {
  return Object.entries(shoppingCart)
    .filter(([_, quantity]) => quantity > 0)
    .map(
      ([productId, quantity]) =>
        getProductName(productId, settings) + " × " + quantity,
    )
    .join(", ");
}

function getProductName(productId: string, settings: BestellWizardSettings) {
  for (const productType of settings.productTypes) {
    for (const product of productType.products) {
      if (product.id === productId) {
        return product.name;
      }
    }
  }
}
