import { useApi } from "../../hooks/useApi.ts";
import { CoopApi } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";

export function updateMinimumNumberOfShares(
  shoppingCartOrder: ShoppingCart,
  shoppingCartWaitingList: ShoppingCart,
  setMinimumNumberOfShares: (num: number) => void,
  setSelectedNumberOfCoopShares: (num: number) => void,
) {
  const coopApi = useApi(CoopApi, getCsrfToken());

  const combinedCart = Object.assign({}, shoppingCartOrder);
  for (const [productId, quantity] of Object.entries(shoppingCartWaitingList)) {
    if (Object.keys(combinedCart).includes(productId)) {
      combinedCart[productId] += quantity;
    } else {
      combinedCart[productId] = quantity;
    }
  }

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
