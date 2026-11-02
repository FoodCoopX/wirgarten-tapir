import { PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { areAllOrderedProductsInWaitingList } from "../../bestell_wizard/utils/areAllOrderedProductsInWaitingList.ts";
import { willBecomeMemberNow } from "./willBecomeMemberNow.ts";

export function isOrderWaitingListOnly(
  settings: BestellWizardSettings,
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  becomeMemberNow: boolean | null,
) {
  if (settings.forceWaitingList) {
    return true;
  }

  return (
    areAllOrderedProductsInWaitingList(
      shoppingCart,
      productTypesInWaitingList,
    ) && !willBecomeMemberNow(settings, becomeMemberNow)
  );
}
