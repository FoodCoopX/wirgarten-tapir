import React from "react";
import { BestellWizardApi, PublicGrowingPeriod } from "../../api-client";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";

export function updateProductsAndProductTypesOverCapacity(
  bestellWizardApi: BestellWizardApi,
  shoppingCart: ShoppingCart,
  setProductIdsOverCapacity: (ids: string[]) => void,
  setProductTypeIdsOverCapacity: (ids: string[]) => void,
  setCheckingCapacities: (enabled: boolean) => void,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  checkingCapacitiesController: AbortController | undefined,
  setCheckingCapacitiesController: React.Dispatch<
    React.SetStateAction<AbortController | undefined>
  >,
  growingPeriod: PublicGrowingPeriod | undefined,
) {
  if (!growingPeriod) {
    return;
  }

  if (checkingCapacitiesController) {
    checkingCapacitiesController.abort();
  }
  const localController = new AbortController();
  setCheckingCapacitiesController(localController);

  setCheckingCapacities(true);

  bestellWizardApi
    .bestellWizardApiBestellWizardCapacityCheckCreate(
      {
        bestellWizardCapacityCheckRequestRequest: {
          shoppingCart: shoppingCart,
          growingPeriodId: growingPeriod.id!,
        },
      },
      { signal: localController.signal },
    )
    .then((response) => {
      setProductIdsOverCapacity(response.idsOfProductsOverCapacity);
      setProductTypeIdsOverCapacity(response.idsOfProductTypesOverCapacity);
      setCheckingCapacities(false);
    })
    .catch((error) => {
      if (error.cause && error.cause.name === "AbortError") return;

      setCheckingCapacities(false);
      handleRequestError(
        error,
        "Fehler beim Laden der Produkt-Kapazitäten: " + error.message,
        setToastDatas,
      );
    });
}
