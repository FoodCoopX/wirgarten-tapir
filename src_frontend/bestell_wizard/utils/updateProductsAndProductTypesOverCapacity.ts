import { handleRequestError } from "../../utils/handleRequestError.ts";
import { useApi } from "../../hooks/useApi.ts";
import { SubscriptionsApi } from "../../api-client";
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
) {
  const subscriptionsApi = useApi(SubscriptionsApi, getCsrfToken());

  setCheckingCapacities(true);

  subscriptionsApi
    .subscriptionsApiBestellWizardCapacityCheckCreate({
      bestellWizardCapacityCheckRequestRequest: {
        shoppingCart: shoppingCart,
      },
    })
    .then((response) => {
      setProductIdsOverCapacity(response.idsOfProductsOverCapacity);
      setProductTypeIdsOverCapacity(response.idsOfProductTypesOverCapacity);
    })
    .catch((error) =>
      handleRequestError(
        error,
        "Fehler beim Laden der Produkt-Kapazitäten: " + error.message,
        setToastDatas,
      ),
    )
    .finally(() => setCheckingCapacities(false));
}
