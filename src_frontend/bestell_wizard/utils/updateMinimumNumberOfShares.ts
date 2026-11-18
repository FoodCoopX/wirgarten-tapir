import React from "react";
import { CoopApi, PublicProductType } from "../../api-client";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { buildFilteredShoppingCart } from "./buildFilteredShoppingCart.ts";

export function updateMinimumNumberOfShares(
  coopApi: CoopApi,
  shoppingCartOrder: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  setMinimumNumberOfShares: (num: number) => void,
  setSelectedNumberOfCoopShares: (num: number) => void,
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>,
) {
  const combinedCart = buildFilteredShoppingCart(
    shoppingCartOrder,
    false,
    productTypesInWaitingList,
  );

  coopApi
    .coopApiMinimumNumberOfSharesRetrieve({
      productIds: Object.keys(combinedCart),
      quantities: Object.values(combinedCart),
    })
    .then((response) => {
      setMinimumNumberOfShares(response.minimumNumberOfShares);
      setSelectedNumberOfCoopShares(response.minimumNumberOfShares);
    })
    .catch((error) =>
      handleRequestError(
        error,
        "Fehler beim Berechnen der Mindestanzahl an Genossenschaftsanteilen",
        setToastDatas,
      ),
    );
}
