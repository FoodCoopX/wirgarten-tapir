import { handleRequestError } from "../../utils/handleRequestError.ts";
import { useApi } from "../../hooks/useApi.ts";
import { BestellWizardApi } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import React from "react";
import { ToastData } from "../../types/ToastData.ts";

export function updateProductsAndProductTypesOverCapacity(
  shoppingCart: ShoppingCart,
  setProductIdsOverCapacity: (ids: string[]) => void,
  setProductTypeIdsOverCapacity: (ids: string[]) => void,
  setCheckingCapacities: (enabled: boolean) => void,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
  checkingCapacitiesController: AbortController | undefined,
  setCheckingCapacitiesController: React.Dispatch<
    React.SetStateAction<AbortController | undefined>
  >,
) {
  const bestellWizardApi = useApi(BestellWizardApi, getCsrfToken());

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
