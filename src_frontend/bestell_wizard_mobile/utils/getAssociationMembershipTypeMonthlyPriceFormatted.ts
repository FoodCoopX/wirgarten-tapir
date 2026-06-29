import { AssociationMembershipType } from "../../api-client";
import { getAssociationMembershipTypeCurrentPrice } from "../../association_memberships_config/getAssociationMembershipTypeCurrentPrice.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";

export function getAssociationMembershipTypeMonthlyPriceFormatted(
  associationMembershipType?: AssociationMembershipType,
) {
  if (!associationMembershipType) {
    return "";
  }

  const currentPrice = getAssociationMembershipTypeCurrentPrice(
    associationMembershipType,
  );

  if (!currentPrice) {
    return "";
  }

  return " " + formatCurrency(currentPrice.priceAsFloat) + " / Monat";
}
