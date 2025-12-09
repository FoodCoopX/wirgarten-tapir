import { BestellWizardApi, PublicGrowingPeriod } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { handleRequestError } from "./handleRequestError.ts";
import { ToastData } from "../types/ToastData.ts";
import React from "react";

export function updateProductPrices(
  selectedGrowingPeriod: PublicGrowingPeriod,
  productPricesController: AbortController | undefined,
  setProductPricesController: (controller: AbortController) => void,
  settings: BestellWizardSettings,
  setSettings: (settings: BestellWizardSettings) => void,
  setToastDatas?: React.Dispatch<React.SetStateAction<ToastData[]>>,
) {
  if (productPricesController) {
    productPricesController.abort();
  }

  const localController = new AbortController();
  setProductPricesController(localController);

  const bestellWizardApi = useApi(BestellWizardApi, "unused");

  bestellWizardApi
    .bestellWizardApiProductPricesRetrieve(
      { growingPeriodId: selectedGrowingPeriod?.id! },
      { signal: localController.signal },
    )
    .then((response) => {
      for (const productType of settings.productTypes) {
        for (const product of productType.products) {
          Object.assign(product, {
            price: getNewPrice(product.id!, response.pricesByProductId),
          });
        }
      }

      setSettings(Object.assign({}, settings));
    })
    .catch(async (error) => {
      if (error.cause && error.cause.name === "AbortError") return;
      await handleRequestError(
        error,
        "Fehler beim Laden der Produkt-Preise",
        setToastDatas,
      );
    });
}

function getNewPrice(
  productIdA: string,
  pricesByProductId: { [productId: string]: number },
) {
  for (const [productIdB, price] of Object.entries(pricesByProductId)) {
    if (productIdA === productIdB) {
      return price;
    }
  }
  return 0;
}
