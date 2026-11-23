import { PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { buildFilteredShoppingCart } from "./buildFilteredShoppingCart.ts";

export function getMinimumNumberOfShares(
  settings: BestellWizardSettings,
  shoppingCart: ShoppingCart,
  productTypesInWaitingList: Set<PublicProductType>,
) {
  if (!settings.showCoopContent) {
    return 0;
  }

  const products = settings.productTypes.flatMap(
    (productType) => productType.products,
  );
  let minimumFromOrder = 0;
  for (const [productId, quantity] of Object.entries(
    buildFilteredShoppingCart(shoppingCart, false, productTypesInWaitingList),
  )) {
    const product = products.find((product) => product.id === productId);
    minimumFromOrder += (product?.minCoopShares ?? 0) * quantity;
  }

  return Math.max(settings.coopMinShares, minimumFromOrder);
}
