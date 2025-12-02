import { areAllOrderedProductsInWaitingList } from "../../bestell_wizard/utils/areAllOrderedProductsInWaitingList.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";

export function shouldConfirmMemberNow(
  settings: BestellWizardSettings,
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
) {
  if (settings.forceWaitingList) {
    return false;
  }

  return areAllOrderedProductsInWaitingList(
    shoppingCart,
    productTypesInWaitingList,
  );
}
