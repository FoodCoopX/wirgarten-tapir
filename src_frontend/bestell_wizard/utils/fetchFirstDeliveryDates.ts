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
    [key: string]: { [key: string]: string };
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
      setFirstDeliveryDatesByPickupLocationIdAndProductTypeId(
        response.deliveryDateByPickupLocationIdAndProductTypeId,
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
