import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { getProductByIdGlobal } from "./getProductByIdGlobal.ts";

export function getProductSolidarityChoices(
  shoppingCart: ShoppingCart,
  settings: BestellWizardSettings,
) {
  const choices = new Set<number>();
  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    if (quantity <= 0) {
      continue;
    }
    const product = getProductByIdGlobal(productId, settings.productTypes);
    for (const choice of product?.solidarityChoices ?? []) {
      choices.add(choice);
    }
  }
  return choices;
}
