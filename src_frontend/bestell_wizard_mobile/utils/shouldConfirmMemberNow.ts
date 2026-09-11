import { PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { areAllOrderedProductsInWaitingList } from "../../bestell_wizard/utils/areAllOrderedProductsInWaitingList.ts";

export function shouldConfirmMemberNow(
  settings: BestellWizardSettings,
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  waitingListConfirmationMode: boolean,
) {
  if (settings.forceWaitingList) {
    return false;
  }

  if (waitingListConfirmationMode) {
    return false;
  }

  return areAllOrderedProductsInWaitingList(
    shoppingCart,
    productTypesInWaitingList,
  );
}
