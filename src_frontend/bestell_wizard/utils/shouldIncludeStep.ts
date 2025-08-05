import { isAtLeastOneOrderedProductWithDelivery } from "./isAtLeastOneOrderedProductWithDelivery.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { PublicProductType, WaitingListEntryDetails } from "../../api-client";

export function shouldIncludeStepIntro(introEnabled: boolean) {
  return introEnabled;
}

export function shouldIncludeStepPickupLocation(
  shoppingCart: ShoppingCart,
  publicProductTypes: PublicProductType[],
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
) {
  if (waitingListEntryDetails !== undefined) {
    return (waitingListEntryDetails.pickupLocationWishes ?? []).length > 0;
  }

  return isAtLeastOneOrderedProductWithDelivery(
    shoppingCart,
    publicProductTypes,
  );
}

export function shouldIncludeStepCoopShares(
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
  waitingListModeEnabled: boolean,
  showCoopContent: boolean,
) {
  if (!showCoopContent) {
    return false;
  }

  if (waitingListEntryDetails === undefined) {
    return !waitingListModeEnabled;
  }

  return !waitingListEntryDetails.memberAlreadyExists;
}

export function shouldIncludeStepPersonalData(
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
) {
  if (waitingListEntryDetails === undefined) {
    return true;
  }

  return (waitingListEntryDetails.productWishes ?? []).length > 0;
}
