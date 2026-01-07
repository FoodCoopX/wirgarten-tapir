import { PublicProduct, PublicProductType } from "../../api-client";
import { shouldShowWarningCurrentOrderIsOverCapacity } from "./shouldShowWarningCurrentOrderIsOverCapacity.ts";
import { shouldShowWarningProductNotAvailable } from "../../utils/shouldShowWarningNotAvailable.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

export function showCapacityWarning(
  product: PublicProduct,
  productType: PublicProductType,
  settings: BestellWizardSettings,
  productTypeIdsOverCapacity: string[],
  productIdsOverCapacity: string[],
  shoppingCart: ShoppingCart,
) {
  return (
    shouldShowWarningCurrentOrderIsOverCapacity(
      productType,
      settings,
      productTypeIdsOverCapacity,
      productIdsOverCapacity,
      shoppingCart,
    ) || shouldShowWarningProductNotAvailable(product, productType, settings)
  );
}
