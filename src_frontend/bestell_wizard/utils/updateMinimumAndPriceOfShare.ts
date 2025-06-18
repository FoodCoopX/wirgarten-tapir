import { useApi } from "../../hooks/useApi.ts";
import { CoopApi } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";

export function updateMinimumAndPriceOfShare(
  shoppingCart: ShoppingCart,
  setMinimumNumberOfShares: (min: number) => void,
  setPriceOfAShare: (price: number) => void,
  selectedNumberOfCoopShares: number,
  setSelectedNumberOfCoopShares: (num: number) => void,
) {
  const coopApi = useApi(CoopApi, "unused");

  coopApi
    .coopApiMinimumNumberOfSharesRetrieve({
      productIds: Object.keys(shoppingCart),
      quantities: Object.values(shoppingCart),
    })
    .then((response) => {
      setMinimumNumberOfShares(response.minimumNumberOfShares);
      setPriceOfAShare(response.priceOfAShare);
      if (selectedNumberOfCoopShares < response.minimumNumberOfShares) {
        setSelectedNumberOfCoopShares(response.minimumNumberOfShares);
      }
    });
}
