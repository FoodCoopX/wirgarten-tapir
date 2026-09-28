import { PublicPickupLocation } from "../api-client";

export function getUniqueDeliveryDays(
  pickupLocations: PublicPickupLocation[],
): number[] {
  const days = new Set(
    pickupLocations
      .map((pickupLocation) => pickupLocation.deliveryDay)
      .filter((day) => day !== null),
  );
  return [...days].sort((a, b) => a - b);
}
