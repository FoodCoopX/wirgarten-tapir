import { PublicProductType } from "../../api-client";

export function sortProductTypes(productTypes: PublicProductType[]) {
  return productTypes.sort((a, b) => {
    return a.orderInBestellwizard! - b.orderInBestellwizard!;
  });
}
