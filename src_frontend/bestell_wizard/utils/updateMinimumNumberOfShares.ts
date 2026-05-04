import { CoopApi, PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { buildFilteredShoppingCart } from "./buildFilteredShoppingCart.ts";

export function updateMinimumNumberOfShares(
  coopApi: CoopApi,
  shoppingCartOrder: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
  setMinimumNumberOfShares: (num: number) => void,
  setSelectedNumberOfCoopShares: (num: number) => void,
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
    });
}
