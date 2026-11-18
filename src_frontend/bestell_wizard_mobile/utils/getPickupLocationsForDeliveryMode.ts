import { PublicPickupLocation } from "../../api-client";
import { DeliveryMode } from "../types/DeliveryMode.ts";

export function getPickupLocationsForDeliveryMode(
  pickupLocations: PublicPickupLocation[],
  deliveryMode: DeliveryMode,
) {
  return pickupLocations.filter(
    (pickupLocation) =>
      pickupLocation.isHomeDelivery === (deliveryMode === "home_delivery"),
  );
}
