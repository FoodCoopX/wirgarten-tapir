import { PublicProduct, PublicProductType } from "../../api-client";

export function getProductByIdGlobal(
  productId: string,
  productTypes: PublicProductType[],
): PublicProduct | undefined {
  for (const productType of productTypes) {
    const product = getProductById(productType, productId);
    if (product) {
      return product;
    }
  }
  return undefined;
}

export function getProductById(
  productType: PublicProductType,
  productId: string,
) {
  return productType.products.find((product) => product.id === productId);
}
