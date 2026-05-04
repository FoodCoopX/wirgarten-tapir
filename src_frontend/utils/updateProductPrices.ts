import React from "react";
import { BestellWizardApi, PublicGrowingPeriod } from "../api-client";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "./handleRequestError.ts";

export function updateProductPrices(
  bestellWizardApi: BestellWizardApi,
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
