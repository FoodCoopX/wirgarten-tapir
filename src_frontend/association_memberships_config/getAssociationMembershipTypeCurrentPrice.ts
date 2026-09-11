import { AssociationMembershipType } from "../api-client";

export function getAssociationMembershipTypeCurrentPrice(
  type: AssociationMembershipType,
  date: Date,
) {
  return type.prices.findLast((price) => price.validFrom <= date);
}
