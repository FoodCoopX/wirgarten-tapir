import { PublicProductType } from "../../api-client";
import { doesProductBelongsToProductType } from "./doesProductBelongToProductType.ts";

export function isProductInWaitingList(
  productId: string,
  productsTypesInWaitingList: Set<PublicProductType>,
): boolean {
  for (const productType of productsTypesInWaitingList) {
    if (doesProductBelongsToProductType(productId, productType)) {
      return true;
    }
  }

  return false;
}
