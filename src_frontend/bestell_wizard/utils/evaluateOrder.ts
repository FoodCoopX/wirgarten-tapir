import React from "react";
import {
  BestellWizardApi,
  BestellWizardGrowingPeriodChoice,
  PublicPickupLocation,
} from "../../api-client";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { isShoppingCartEmpty } from "./isShoppingCartEmpty.ts";

export function evaluateOrder(
  bestellWizardApi: BestellWizardApi,
  shoppingCart: ShoppingCart,
  growingPeriod: BestellWizardGrowingPeriodChoice,
  pickupLocations: PublicPickupLocation[],
  ignoreOverCapacityLists: boolean,
  setOrderEvaluationLoading: (loading: boolean) => void,
  setProductIdsOverCapacity: (ids: string[]) => void,
  setProductTypeIdsOverCapacity: (ids: string[]) => void,
  setPickupLocationsWithCapacityFull: (
    pickupLocations: Set<PublicPickupLocation>,
  ) => void,
  setFirstDeliveryDatesByPickupLocationAndProductType: (dates: {
    [key: string]: { [key: string]: string };
  }) => void,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  isIgnored: () => boolean,
) {
  if (isShoppingCartEmpty(shoppingCart)) {
    setOrderEvaluationLoading(false);
    setProductIdsOverCapacity([]);
    setProductTypeIdsOverCapacity([]);
    setPickupLocationsWithCapacityFull(new Set());
    setFirstDeliveryDatesByPickupLocationAndProductType({});
    return;
  }

  setOrderEvaluationLoading(true);

  bestellWizardApi
    .bestellWizardApiOrderEvaluationCreate({
      bestellWizardOrderEvaluationRequestRequest: {
        shoppingCart: shoppingCart,
        growingPeriodId: growingPeriod.id!,
      },
    })
    .then((response) => {
      if (isIgnored()) return;

      if (!ignoreOverCapacityLists) {
        setProductIdsOverCapacity(response.idsOfProductsOverCapacity);
        setProductTypeIdsOverCapacity(response.idsOfProductTypesOverCapacity);
      }
      setPickupLocationsWithCapacityFull(
        new Set(
          pickupLocations.filter(
            (pickupLocation) =>
              !response.pickupLocationIdsWithEnoughCapacityForOrder.includes(
                pickupLocation.id,
              ),
          ),
        ),
      );
      setFirstDeliveryDatesByPickupLocationAndProductType(
        response.deliveryDateByPickupLocationIdAndProductTypeId,
      );
    })
    .catch((error) => {
      if (isIgnored()) return;
      handleRequestError(
        error,
        "Fehler bei der Prüfung der Bestellung: " + error.message,
        setToastDatas,
      );
    })
    .finally(() => {
      if (isIgnored()) return;
      setOrderEvaluationLoading(false);
    });
}
