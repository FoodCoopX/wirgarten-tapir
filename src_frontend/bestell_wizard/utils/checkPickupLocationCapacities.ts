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
  setPickupLocationsWithCapacityCheckLoading: React.Dispatch<
    React.SetStateAction<Set<PublicPickupLocation>>
  >,
  setPickupLocationsWithCapacityFull: React.Dispatch<
    React.SetStateAction<Set<PublicPickupLocation>>
  >,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  growingPeriod: PublicGrowingPeriod | undefined,
) {
  setPickupLocationsWithCapacityCheckLoading(new Set(pickupLocations));

  for (const pickupLocation of pickupLocations) {
    pickupLocationApi
      .pickupLocationsApiPickupLocationCapacityCheckCreate({
        pickupLocationCapacityCheckRequestRequest: {
          pickupLocationId: pickupLocation.id!,
          shoppingCart: shoppingCart,
          growingPeriodId: growingPeriod ? growingPeriod.id! : null,
        },
      })
      .then((response) => {
        setPickupLocationsWithCapacityFull((set) => {
          if (response.enoughCapacityForOrder) {
            set.delete(pickupLocation);
          } else {
            set.add(pickupLocation);
          }
          return new Set(set);
        });
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
        setPickupLocationsWithCapacityCheckLoading((set) => {
          set.delete(pickupLocation);
          return new Set(set);
        });
      });
  }
}
