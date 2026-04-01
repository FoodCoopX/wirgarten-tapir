import { PublicProduct, PublicProductType } from "../api-client";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";

export function shouldShowWarningProductNotAvailable(
  product: PublicProduct,
  productType: PublicProductType,
  settings: BestellWizardSettings,
) {
  if (settings.productIdsThatAreAlreadyAtCapacity.includes(product.id!)) {
    return true;
  }

  if (shouldShowWarningProductTypeNotAvailable(productType, settings)) {
    return true;
  }

  return settings.forceWaitingList;
}

export function shouldShowWarningProductTypeNotAvailable(
  productType: PublicProductType,
  settings: BestellWizardSettings,
) {
  if (productType.forceWaitingList) {
    return true;
  }

  if (
    settings.productTypeIdsThatAreAlreadyAtCapacity.includes(productType.id!)
  ) {
    return true;
  }

  return settings.forceWaitingList;
}
