import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import {
  shouldIncludeStepCoopShares,
  shouldIncludeStepIntro,
  shouldIncludeStepPersonalData,
  shouldIncludeStepPickupLocation
} from "./shouldIncludeStep.ts";
import { type PublicProductType, WaitingListEntryDetails } from "../../api-client";

export function buildSteps(
  settings: BestellWizardSettings,
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
  shoppingCartOrder: ShoppingCart,
  shoppingCartWaitingList: ShoppingCart,
  selectedProductTypes: PublicProductType[],
) {
  let newSteps = [];

  if (shouldIncludeStepIntro(settings.introEnabled, waitingListEntryDetails)) {
    newSteps.push("intro");
  }

  newSteps.push(
    ...getRelevantProductSteps(
      true,
      selectedProductTypes,
      waitingListEntryDetails,
      settings,
    ),
  );

  if (
    shouldIncludeStepPickupLocation(
      shoppingCartOrder,
      settings.productTypes,
      waitingListEntryDetails,
    )
  ) {
    newSteps.push("pickup_location");
  }

  newSteps.push(
    ...getRelevantProductSteps(
      false,
      selectedProductTypes,
      waitingListEntryDetails,
      settings,
    ),
  );

  if (
    shouldIncludeStepCoopShares(
      waitingListEntryDetails,
      shoppingCartOrder,
      shoppingCartWaitingList,
      settings.showCoopContent,
    )
  ) {
    newSteps.push("coop_shares");
  }

  if (shouldIncludeStepPersonalData(waitingListEntryDetails)) {
    newSteps.push("personal_data");
  }

  newSteps.push("summary", "end");

  return newSteps;
}

function getRelevantProductSteps(
  withDelivery: boolean,
  selectedProductTypes: PublicProductType[],
  waitingListEntryDetails: WaitingListEntryDetails | undefined,
  settings: BestellWizardSettings,
) {
  let productSteps = selectedProductTypes;
  if (!settings.introEnabled && waitingListEntryDetails === undefined) {
    productSteps = settings.productTypes;
  }
  productSteps = productSteps.filter(
    (productType) => productType.noDelivery !== withDelivery,
  );
  return productSteps.map((productType) => productType.id!);
}
