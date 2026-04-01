import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

export function getFirstDelivery(
  pickupLocationId: string,
  firstDeliveryDatesByPickupLocationAndProductType: {
    [key: string]: { [key: string]: Date };
  },
) {
  let dateAsString = "Kapazität frei";

  if (
    pickupLocationId in firstDeliveryDatesByPickupLocationAndProductType &&
    Object.values(
      firstDeliveryDatesByPickupLocationAndProductType[pickupLocationId],
    ).length > 0
  ) {
    let minDate = Object.values(
      firstDeliveryDatesByPickupLocationAndProductType[pickupLocationId],
    )[0];

    for (const date of Object.values(
      firstDeliveryDatesByPickupLocationAndProductType[pickupLocationId],
    )) {
      if (date < minDate) {
        minDate = date;
      }
    }

    dateAsString = "Erste Lieferung: " + formatDateNumeric(minDate);
  }

  return dateAsString;
}
