import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function getProductTypeByProductId(
  productId: string,
  settings: BestellWizardSettings,
) {
  for (const productType of settings.productTypes) {
    for (const product of productType.products) {
      if (product.id === productId) {
        return productType;
      }
    }
  }
}
