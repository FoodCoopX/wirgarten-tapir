import { AssociationMembershipType } from "../api-client";
import { toApiDate } from "../utils/apiDate.ts";

export function getAssociationMembershipTypeCurrentPrice(
  type: AssociationMembershipType,
  date: Date,
) {
  const dateAsString = toApiDate(date);
  return type.prices.findLast((price) => price.validFrom <= dateAsString);
}
