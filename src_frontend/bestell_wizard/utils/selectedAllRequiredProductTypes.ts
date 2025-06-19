import { PublicProductType } from "../../api-client";

export function selectedAllRequiredProductTypes(
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
