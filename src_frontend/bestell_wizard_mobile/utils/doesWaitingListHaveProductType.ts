import { PublicProductType } from "../../api-client";

export function doesWaitingListHaveProductType(
  productTypesInWaitingList: Set<PublicProductType>,
  productType: PublicProductType,
) {
  // We can't use productTypesInWaitingList.has() because that would compare by object ID, not by product ID.
  return [...productTypesInWaitingList].some(
    (otherProductType) => otherProductType.id === productType.id,
  );
}
