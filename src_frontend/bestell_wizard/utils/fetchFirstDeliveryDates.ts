import { BestellWizardApi, PublicPickupLocation } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import { ToastData } from "../../types/ToastData.ts";
import React from "react";

export function fetchFirstDeliveryDates(
  pickupLocations: PublicPickupLocation[],
  shoppingCart: ShoppingCart,
  setFirstDeliveryDatesByProductType: (map: { [key: string]: Date }) => void,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  waitingListEntryId: string | undefined,
) {
  if (pickupLocations.length === 0) {
    return;
  }
  const bestellWizardApi = useApi(BestellWizardApi, getCsrfToken());

  bestellWizardApi
    .bestellWizardApiBestellWizardDeliveryDatesCreate({
      bestellWizardDeliveryDatesForOrderRequestRequest: {
        pickupLocationId: pickupLocations[0].id!,
        shoppingCart: shoppingCart,
        waitingListEntryId: waitingListEntryId,
      },
    })
    .then((response) => {
      const entries = Object.entries(
        response.productTypeIdToNextDeliveryDateMap,
      );

      setFirstDeliveryDatesByProductType(
        Object.fromEntries(
          entries.map(([productId, dateAsString]) => [
            productId,
            new Date(dateAsString as unknown as string), //The generated client say that the values are Dates, but they are actually strings
          ]),
        ),
      );
    })
    .catch((error) =>
      handleRequestError(
        error,
        "Fehler beim Laden der Lieferungsdaten: " + error.message,
        setToastDatas,
      ),
    );
}
