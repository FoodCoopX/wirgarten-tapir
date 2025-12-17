import { PublicPickupLocation } from "../../api-client";

export function getFirstPickupLocationWithCapacity(
  selectedPickupLocations: PublicPickupLocation[],
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>,
) {
  for (const pickupLocation of selectedPickupLocations) {
    if (!pickupLocationsWithCapacityFull.has(pickupLocation)) {
      return pickupLocation;
    }
  }
}
