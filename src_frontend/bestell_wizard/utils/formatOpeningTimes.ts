import {
  PickupLocationOpeningTime,
  PublicPickupLocation,
} from "../../api-client";

function compareOpeningTimes(
  a: PickupLocationOpeningTime,
  b: PickupLocationOpeningTime,
) {
  if (a.dayOfWeek !== b.dayOfWeek) {
    return a.dayOfWeek - b.dayOfWeek;
  }

  return (
    parseInt(a.openTime.split(":")[0]) - parseInt(b.openTime.split(":")[0])
  );
}

export function formatOpeningTimes(pickupLocation: PublicPickupLocation) {
  return pickupLocation.openingTimes
    .sort(compareOpeningTimes)
    .map((openingTime) => {
      return (
        openingTime.dayOfWeekString.substring(0, 2) +
        " " +
        openingTime.openTime.substring(0, 5) +
        "-" +
        openingTime.closeTime.substring(0, 5)
      );
    })
    .join(", ");
}
