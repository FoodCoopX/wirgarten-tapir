import { handleRequestError } from "../../utils/handleRequestError.ts";
import { useApi } from "../../hooks/useApi.ts";
import { PickupLocationsApi, PublicPickupLocation } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import React from "react";

export function checkPickupLocationCapacities(
  pickupLocations: PublicPickupLocation[],
  shoppingCart: ShoppingCart,
  setPickupLocationsWithCapacityCheckLoading: React.Dispatch<
    React.SetStateAction<Set<PublicPickupLocation>>
  >,
  setPickupLocationsWithCapacityFull: React.Dispatch<
    React.SetStateAction<Set<PublicPickupLocation>>
  >,
) {
  const pickupLocationApi = useApi(PickupLocationsApi, "unused");

  setPickupLocationsWithCapacityCheckLoading(new Set(pickupLocations));

  for (const pickupLocation of pickupLocations) {
    pickupLocationApi
      .pickupLocationsApiPickupLocationCapacityCheckCreate({
        pickupLocationCapacityCheckRequestRequest: {
          pickupLocationId: pickupLocation.id!,
          shoppingCart: shoppingCart,
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
      .catch(handleRequestError)
      .finally(() => {
        setPickupLocationsWithCapacityCheckLoading((set) => {
          set.delete(pickupLocation);
          return new Set(set);
        });
      });
  }
}
