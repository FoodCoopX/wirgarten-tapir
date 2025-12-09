import { BestellWizardApi, PublicGrowingPeriod } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import { ToastData } from "../../types/ToastData.ts";
import React from "react";

export function fetchFirstDeliveryDates(
  shoppingCart: ShoppingCart,
  selectedGrowingPeriod: PublicGrowingPeriod,
  setFirstDeliveryDatesByPickupLocationIdAndProductTypeId: (map: {
    [key: string]: { [key: string]: Date };
  }) => void,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  waitingListEntryId: string | undefined,
) {
  const bestellWizardApi = useApi(BestellWizardApi, getCsrfToken());

  bestellWizardApi
    .bestellWizardApiBestellWizardDeliveryDatesCreate({
      bestellWizardDeliveryDatesForOrderRequestRequest: {
        shoppingCart: shoppingCart,
        waitingListEntryId: waitingListEntryId,
        growingPeriodId: selectedGrowingPeriod.id,
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
