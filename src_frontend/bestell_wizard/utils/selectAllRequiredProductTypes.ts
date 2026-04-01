import { PublicProductType } from "../../api-client";

export function selectAllRequiredProductTypes(
  productTypes: PublicProductType[],
  selectedProductTypes: PublicProductType[],
  setSelectedProductTypes: (types: PublicProductType[]) => void,
) {
  setSelectedProductTypes(
    productTypes.filter(
      (productType) =>
        productType.mustBeSubscribedTo ||
        selectedProductTypes.includes(productType),
    ),
  );
}
