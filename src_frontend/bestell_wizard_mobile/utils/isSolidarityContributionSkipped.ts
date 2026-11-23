import {
  PublicProductType,
  PublicWaitingListEntryDetails,
} from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { isOrderWaitingListOnly } from "./isOrderWaitingListOnly.ts";

export function isSolidarityContributionSkipped(
  settings: BestellWizardSettings,
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  becomeMemberNow: boolean | null,
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined,
) {
  return (
    waitingListEntryDetails === undefined &&
    isOrderWaitingListOnly(
      settings,
      shoppingCart,
      productTypesInWaitingList,
      becomeMemberNow,
    )
  );
}
