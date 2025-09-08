import { useApi } from "../../hooks/useApi.ts";
import { CoopApi } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";

export function updateMinimumNumberOfShares(
  shoppingCart: ShoppingCart,
  setMinimumNumberOfShares: (num: number) => void,
  setSelectedNumberOfCoopShares: (num: number) => void,
) {
  const coopApi = useApi(CoopApi, getCsrfToken());

  coopApi
    .coopApiMinimumNumberOfSharesRetrieve({
      productIds: Object.keys(shoppingCart),
      quantities: Object.values(shoppingCart),
    })
    .then((response) => {
      setMinimumNumberOfShares(response.minimumNumberOfShares);
      setSelectedNumberOfCoopShares(response.minimumNumberOfShares);
    });
}
