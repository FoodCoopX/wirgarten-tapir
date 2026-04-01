import type { PublicProductType } from "../../api-client";

export function doesProductBelongsToProductType(
  productId: string,
  productType: PublicProductType,
) {
  for (const product of productType.products) {
    if (product.id === productId) {
      return true;
    }
  }
  return false;
}
