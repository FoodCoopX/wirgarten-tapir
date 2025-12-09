import { Step } from "../types/Step.ts";
import { isAtLeastOneOrderedProductWithDelivery } from "../../bestell_wizard/utils/isAtLeastOneOrderedProductWithDelivery.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import {
  PublicGrowingPeriod,
  PublicPickupLocation,
  PublicProductType,
} from "../../api-client";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { shouldConfirmMemberNow } from "./shouldConfirmMemberNow.ts";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import { buildFilteredShoppingCart } from "../../bestell_wizard/utils/buildFilteredShoppingCart.ts";
import { areAllOrderedProductsInWaitingList } from "../../bestell_wizard/utils/areAllOrderedProductsInWaitingList.ts";
import dayjs from "dayjs";

export function buildSteps(
  settings: BestellWizardSettings,
  selectedProductTypes: PublicProductType[],
  shoppingCart: ShoppingCart,
  becomeMemberNow: boolean | null,
  productTypesInWaitingList: Set<PublicProductType>,
  selectedPickupLocation: PublicPickupLocation[],
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>,
  solidarityContribution: number,
) {
  const newSteps: Step[] = [];
  newSteps.push(
    settings.forceWaitingList ? "1b_welcome_waiting_list" : "1a_welcome",
  );
  newSteps.push("2_first_name");

  if (settings.introEnabled) {
    newSteps.push("3_product_type_choice");
  }

  if (shouldIncludeStepGrowingPeriodChoice(settings.growingPeriodChoices)) {
    newSteps.push("3b_growing_period_choice");
  }

  for (const productType of selectedProductTypes) {
    if (!productType.noDelivery) {
      newSteps.push(productType.id! + "_intro");
      newSteps.push(productType.id! + "_order");
    }
  }

  if (
    settings.pickupLocations.length > 0 &&
    isAtLeastOneOrderedProductWithDelivery(shoppingCart, settings.productTypes)
  ) {
    newSteps.push("5a_pickup_location_intro");
    newSteps.push("5b_pickup_location_choice");

    if (
      selectedPickupLocation.length === 1 &&
      pickupLocationsWithCapacityFull.has(selectedPickupLocation[0])
    ) {
      newSteps.push("5c_pickup_location_confirm_waiting_list");
    }
  }

  for (const productType of selectedProductTypes) {
    if (productType.noDelivery) {
      newSteps.push(productType.id! + "_intro");
      newSteps.push(productType.id! + "_order");
    }
  }

  if (settings.showCoopContent) {
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

  newSteps.push("7_solidarity_contribution");
  newSteps.push("8_personal_data");

  if (
    isAtLeastOneProductOrdered(
      buildFilteredShoppingCart(shoppingCart, false, productTypesInWaitingList),
    ) ||
    becomeMemberNow !== false ||
    solidarityContribution > 0
  ) {
    newSteps.push("9_banking_data");
  }

  newSteps.push("10_summary");
  newSteps.push("11_legal");
  newSteps.push("12_channel");

  if (settings.feedbackStepEnabled) {
    newSteps.push("13_feedback");
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

function shouldIncludeStepGrowingPeriodChoice(choices: PublicGrowingPeriod[]) {
  if (choices.length > 1) {
    return true;
  }

  if (choices.length === 1) {
    const period = choices[0];
    return dayjs().add(31, "days").isBefore(dayjs(period.startDate));
  }

  return false;
}
