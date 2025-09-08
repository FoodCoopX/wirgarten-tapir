import {
  PublicPickupLocation,
  WaitingListEntryDetails,
} from "../../api-client";

export function sortPickupLocationsByWaitingListWishes(
  pickupLocations: PublicPickupLocation[],
  waitingListEntryDetails?: WaitingListEntryDetails,
) {
  if (
    waitingListEntryDetails === undefined ||
    waitingListEntryDetails.pickupLocationWishes === undefined ||
    waitingListEntryDetails.pickupLocationWishes.length === 0
  ) {
    return;
  }

  const pickupLocationId =
    waitingListEntryDetails.pickupLocationWishes[0].pickupLocation.id;

  pickupLocations.sort((a, b) => {
    if (a.id === pickupLocationId) {
      return -1;
    }
    if (b.id === pickupLocationId) {
      return 1;
    }
    return 0;
  });
}
