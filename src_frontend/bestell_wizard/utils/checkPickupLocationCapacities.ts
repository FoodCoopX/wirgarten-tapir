import React from "react";
import {
  PickupLocationsApi,
  PublicGrowingPeriod,
  PublicPickupLocation,
} from "../../api-client";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";

export function checkPickupLocationCapacities(
  pickupLocationApi: PickupLocationsApi,
  pickupLocations: PublicPickupLocation[],
  shoppingCart: ShoppingCart,
  setPickupLocationsCapacityCheckLoading: React.Dispatch<
    React.SetStateAction<boolean>
  >,
  setPickupLocationsWithCapacityFull: React.Dispatch<
    React.SetStateAction<Set<PublicPickupLocation>>
  >,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  growingPeriod: PublicGrowingPeriod | undefined,
) {
  setPickupLocationsCapacityCheckLoading(true);

  pickupLocationApi
    .pickupLocationsApiPickupLocationCapacityCheckCreate({
      pickupLocationCapacityCheckRequestRequest: {
        shoppingCart: shoppingCart,
        growingPeriodId: growingPeriod ? growingPeriod.id! : null,
      },
    })
    .then((response) => {
      setPickupLocationsWithCapacityFull(
        new Set(
          pickupLocations.filter(
            (location) =>
              !response.pickupLocationIdsWithEnoughCapacityForOrder.includes(
                location.id!,
              ),
          ),
        ),
      );
    })
    .catch((error) =>
      handleRequestError(
        error,
        "Fehler bei der Bestätigung der Verteilstationen-Kapazitäten: " +
          error.message,
        setToastDatas,
      ),
    )
    .finally(() => {
      setPickupLocationsCapacityCheckLoading(false);
    });
}
