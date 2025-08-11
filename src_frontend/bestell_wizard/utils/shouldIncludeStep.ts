import { isAtLeastOneOrderedProductWithDelivery } from "./isAtLeastOneOrderedProductWithDelivery.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { PublicProductType, WaitingListEntryDetails } from "../../api-client";

export function shouldIncludeStepIntro(
  introEnabled: boolean,
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
) {
  if (waitingListEntryDetails) {
    return false;
  }

  return introEnabled;
}

export function shouldIncludeStepPickupLocation(
  shoppingCart: ShoppingCart,
  publicProductTypes: PublicProductType[],
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
) {
  if (waitingListEntryDetails === undefined) {
    return isAtLeastOneOrderedProductWithDelivery(
      shoppingCart,
      publicProductTypes,
    );
  }

  return (waitingListEntryDetails.pickupLocationWishes ?? []).length > 0;
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

  if (waitingListEntryDetails.memberAlreadyExists) {
    return waitingListEntryDetails.numberOfCoopShares > 0;
  }

  return true;
}

export function shouldIncludeStepPersonalData(
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
) {
  if (waitingListEntryDetails === undefined) {
    return true;
  }

  return (waitingListEntryDetails.productWishes ?? []).length > 0;
}
