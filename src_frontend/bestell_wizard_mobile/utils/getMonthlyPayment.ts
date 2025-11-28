import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { getProductById } from "./getProductByIdGlobal.ts";

export function getMonthlyPayment(
  solidarityContribution: number,
  shoppingCart: ShoppingCart,
  settings: BestellWizardSettings,
) {
  let monthlyPayment = solidarityContribution;
  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    for (const productType of settings.productTypes) {
      const product = getProductById(productType, productId);
      if (!product) {
        continue;
      }
      monthlyPayment += product.price * quantity;
    }
  }

  return monthlyPayment;
}
