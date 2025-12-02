import { PublicProductType } from "../../api-client";
import { doesProductBelongsToProductType } from "./doesProductBelongToProductType.ts";

export function isProductInWaitingList(
  productId: string,
  productTypesInWaitingList: Set<PublicProductType>,
): boolean {
  for (const productType of productTypesInWaitingList) {
    if (doesProductBelongsToProductType(productId, productType)) {
      return true;
    }
  }

  return false;
}
