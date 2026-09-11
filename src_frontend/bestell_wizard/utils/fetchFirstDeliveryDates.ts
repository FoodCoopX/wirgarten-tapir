import React from "react";
import { BestellWizardApi, PublicGrowingPeriod } from "../../api-client";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";

export function fetchFirstDeliveryDates(
  bestellWizardApi: BestellWizardApi,
  shoppingCart: ShoppingCart,
  selectedGrowingPeriod: PublicGrowingPeriod | undefined,
  setFirstDeliveryDatesByPickupLocationIdAndProductTypeId: (map: {
    [key: string]: { [key: string]: Date };
  }) => void,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  waitingListEntryId: string | undefined,
) {
  bestellWizardApi
    .bestellWizardApiBestellWizardDeliveryDatesCreate({
      bestellWizardDeliveryDatesForOrderRequestRequest: {
        shoppingCart: shoppingCart,
        waitingListEntryId: waitingListEntryId,
        growingPeriodId: selectedGrowingPeriod?.id,
      },
    })
    .then((response) => {
      const dates: { [key: string]: { [key: string]: Date } } = {};

      const byPickupLocationId = Object.entries(
        response.deliveryDateByPickupLocationIdAndProductTypeId,
      );

      for (const [pickupLocationId, byProductTypeId] of byPickupLocationId) {
        dates[pickupLocationId] = {};

        for (const [productTypeId, dateAsString] of Object.entries(
          byProductTypeId,
        )) {
          dates[pickupLocationId][productTypeId] = new Date(
            dateAsString as unknown as string,
          ); //The generated client say that the values are Dates, but they are actually strings
        }
      }
      setFirstDeliveryDatesByPickupLocationIdAndProductTypeId(dates);
    })
    .catch((error) =>
      handleRequestError(
        error,
        "Fehler beim Laden der Lieferungsdaten: " + error.message,
        setToastDatas,
      ),
    );
}
