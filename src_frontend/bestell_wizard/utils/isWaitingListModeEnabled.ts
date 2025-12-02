import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";
import { areAllOrderedProductsInWaitingList } from "./areAllOrderedProductsInWaitingList.ts";

export function isWaitingListModeEnabled(
  settings: BestellWizardSettings,
  shoppingCartOrder: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  becomeMemberNow: boolean | null,
) {
  return (
    settings.forceWaitingList ||
    (areAllOrderedProductsInWaitingList(
      shoppingCartOrder,
      productTypesInWaitingList,
    ) &&
      becomeMemberNow === false)
  );
}
