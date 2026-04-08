import { Step } from "../types/Step.ts";
import { isAtLeastOneOrderedProductWithDelivery } from "../../bestell_wizard/utils/isAtLeastOneOrderedProductWithDelivery.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import {
  PublicPickupLocation,
  PublicProductType,
  PublicWaitingListEntryDetails,
} from "../../api-client";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { shouldConfirmMemberNow } from "./shouldConfirmMemberNow.ts";
import { areAllOrderedProductsInWaitingList } from "../../bestell_wizard/utils/areAllOrderedProductsInWaitingList.ts";
import { shouldIncludeStepGrowingPeriodChoice } from "./shouldIncludeStepGrowingPeriodChoice.ts";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";

export function buildSteps(
  settings: BestellWizardSettings,
  selectedProductTypes: PublicProductType[],
  shoppingCart: ShoppingCart,
  becomeMemberNow: boolean | null,
  productTypesInWaitingList: Set<PublicProductType>,
  selectedPickupLocation: PublicPickupLocation[],
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>,
  waitingListEntryDetails?: PublicWaitingListEntryDetails,
) {
  const newSteps: Step[] = [];
  newSteps.push(
    settings.forceWaitingList ? "1b_welcome_waiting_list" : "1a_welcome",
    "2_first_name",
  );

  if (settings.introEnabled && waitingListEntryDetails === undefined) {
    newSteps.push("3_product_type_choice");
  }

  if (
    shouldIncludeStepGrowingPeriodChoice(
      selectedProductTypes,
      settings.growingPeriodChoices,
    )
  ) {
    newSteps.push("3b_growing_period_choice");
  }

  for (const productType of selectedProductTypes) {
    if (!productType.noDelivery) {
      newSteps.push(productType.id! + "_intro", productType.id! + "_order");
    }
  }

  if (
    shouldShowStepSolidarityContributionBeforeStepPickupLocation(
      settings,
      waitingListEntryDetails,
      shoppingCart,
    )
  ) {
    newSteps.push("7_solidarity_contribution");
  }

  if (
    shouldIncludeStepsPickupLocations(
      settings,
      waitingListEntryDetails,
      shoppingCart,
    )
  ) {
    newSteps.push("5a_pickup_location_intro", "5b_pickup_location_choice");

    if (
      selectedPickupLocation.length === 1 &&
      pickupLocationsWithCapacityFull.has(selectedPickupLocation[0]) &&
      !waitingListEntryDetails
    ) {
      newSteps.push("5c_pickup_location_confirm_waiting_list");
    }
  }

  for (const productType of selectedProductTypes) {
    if (productType.noDelivery) {
      newSteps.push(productType.id! + "_intro", productType.id! + "_order");
    }
  }

  if (
    shouldIncludeStepsCoopShares(
      waitingListEntryDetails,
      settings.showCoopContent,
    )
  ) {
    newSteps.push("6a_coop_intro");

    if (
      shouldConfirmMemberNow(settings, shoppingCart, productTypesInWaitingList)
    ) {
      newSteps.push("6c_coop_member_now");
    }

    if (becomeMemberNow !== false) {
      newSteps.push("6b_coop_shares");
    }
  }

  if (
    shouldShowStepSolidarityContributionBeforeStepPersonalData(
      settings,
      waitingListEntryDetails,
      shoppingCart,
    )
  ) {
    newSteps.push("7_solidarity_contribution");
  }

  newSteps.push("8_personal_data");

  if (
    becomeMemberNow !== false &&
    !waitingListEntryDetails?.memberAlreadyExists
  ) {
    newSteps.push("9_banking_data");
  }

  newSteps.push("10_summary", "11_legal");

  if (!waitingListEntryDetails?.memberAlreadyExists) {
    newSteps.push("12_channel");
    if (settings.feedbackStepEnabled) {
      newSteps.push("13_feedback");
    }
  }

  if (
    areAllOrderedProductsInWaitingList(
      shoppingCart,
      productTypesInWaitingList,
    ) &&
    becomeMemberNow === false
  ) {
    newSteps.push("14b_confirmation_waiting_list");
  } else {
    newSteps.push("14_confirmation");
  }

  return newSteps;
}

function shouldIncludeStepsCoopShares(
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined,
  showCoopContent: boolean,
) {
  if (!showCoopContent) {
    return false;
  }

  if (waitingListEntryDetails?.memberAlreadyExists) {
    return waitingListEntryDetails.numberOfCoopShares > 0;
  }

  return true;
}

function shouldIncludeStepsPickupLocations(
  settings: BestellWizardSettings,
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined,
  shoppingCart: ShoppingCart,
) {
  if (settings.pickupLocations.length === 0) {
    return false;
  }

  if (waitingListEntryDetails !== undefined) {
    return (waitingListEntryDetails.pickupLocationWishes ?? []).length > 0;
  }

  return isAtLeastOneOrderedProductWithDelivery(
    shoppingCart,
    settings.productTypes,
  );
}

function shouldShowStepSolidarityContribution(
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined,
) {
  if (waitingListEntryDetails === undefined) {
    return true;
  }

  return !waitingListEntryDetails.memberAlreadyExists;
}

function shouldShowStepSolidarityContributionBeforeStepPickupLocation(
  settings: BestellWizardSettings,
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined,
  shoppingCart: ShoppingCart,
) {
  if (!shouldShowStepSolidarityContribution(waitingListEntryDetails)) {
    return false;
  }

  if (settings.solidarityStepPosition !== "before_pickup_location") {
    return false;
  }

  return isAtLeastOneProductOrdered(shoppingCart);
}

function shouldShowStepSolidarityContributionBeforeStepPersonalData(
  settings: BestellWizardSettings,
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined,
  shoppingCart: ShoppingCart,
) {
  if (!shouldShowStepSolidarityContribution(waitingListEntryDetails)) {
    return false;
  }

  return (
    settings.solidarityStepPosition === "before_personal_data" ||
    !shouldShowStepSolidarityContributionBeforeStepPickupLocation(
      settings,
      waitingListEntryDetails,
      shoppingCart,
    )
  );
}
