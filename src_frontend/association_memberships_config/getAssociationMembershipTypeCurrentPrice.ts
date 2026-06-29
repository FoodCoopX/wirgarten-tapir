import { AssociationMembershipType } from "../api-client";

export function getAssociationMembershipTypeCurrentPrice(
  type: AssociationMembershipType,
) {
  const now = new Date();
  return type.prices.findLast((price) => price.validFrom < now);
}
