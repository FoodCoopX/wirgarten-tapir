import { PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function shouldProductTypeBeRemovedFromWaitingList(
  productType: PublicProductType,
  settings: BestellWizardSettings,
  productTypeIdsOverCapacity: string[],
  productIdsOverCapacity: string[],
) {
  if (settings.forceWaitingList) {
    return false;
  }

  if (productType.forceWaitingList) {
    return false;
  }

  if (productTypeIdsOverCapacity.includes(productType.id!)) {
    return false;
  }

  for (const product of productType.products) {
    if (productIdsOverCapacity.includes(product.id!)) {
      return false;
    }
  }

  return true;
}
