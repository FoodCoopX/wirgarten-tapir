import dayjs from "dayjs";
import { PublicPickupLocation } from "../../api-client";

export function isPickupLocationFuture(
  pickupLocation: PublicPickupLocation,
  contractStartDate: Date | undefined,
): boolean {
  if (!pickupLocation.startDate || !contractStartDate) {
    return false;
  }

  return dayjs(pickupLocation.startDate).isAfter(dayjs(contractStartDate), "day");
}

export function getEffectiveContractStartDate(
  contractStartDate: Date | undefined,
  pickupLocation: PublicPickupLocation | undefined,
  growingPeriodEndDate?: Date,
): Date | undefined {
  if (!contractStartDate) {
    return undefined;
  }

  if (
    pickupLocation?.startDate &&
    dayjs(pickupLocation.startDate).isAfter(dayjs(contractStartDate), "day")
  ) {
    if (
      growingPeriodEndDate &&
      dayjs(pickupLocation.startDate).isAfter(
        dayjs(growingPeriodEndDate),
        "day",
      )
    ) {
      return undefined;
    }
    return dayjs(pickupLocation.startDate).toDate();
  }

  return contractStartDate;
}