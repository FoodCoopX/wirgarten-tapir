import { AssociationMembershipType } from "../api-client";

export function getAssociationMembershipTypeCurrentPrice(
  type: AssociationMembershipType,
  date: Date | undefined,
) {
  if (!date) {
    return undefined;
  }
  return type.prices.findLast((price) => price.validFrom <= date);
}
