import { useApi } from "../../hooks/useApi.ts";
import { CoopApi, PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import { buildFilteredShoppingCart } from "./buildFilteredShoppingCart.ts";

export function updateMinimumNumberOfShares(
  shoppingCartOrder: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  setMinimumNumberOfShares: (num: number) => void,
  setSelectedNumberOfCoopShares: (num: number) => void,
) {
  const coopApi = useApi(CoopApi, getCsrfToken());

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
    });
}
