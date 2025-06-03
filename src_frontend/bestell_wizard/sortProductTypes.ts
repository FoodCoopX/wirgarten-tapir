import { PublicProductType } from "../api-client";

export function sortProductTypes(productTypes: PublicProductType[]) {
  return productTypes.sort(
    (a, b) => a.orderInBestellwizard! - b.orderInBestellwizard!,
  );
}
