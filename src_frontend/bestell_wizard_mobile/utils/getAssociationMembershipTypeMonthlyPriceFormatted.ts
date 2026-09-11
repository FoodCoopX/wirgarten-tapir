import { AssociationMembershipType } from "../../api-client";
import { getAssociationMembershipTypeCurrentPrice } from "../../association_memberships_config/getAssociationMembershipTypeCurrentPrice.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";

export function getAssociationMembershipTypeMonthlyPriceFormatted(
  associationMembershipType?: AssociationMembershipType,
  contractStartDate?: Date,
) {
  if (!associationMembershipType || !contractStartDate) {
    return "";
  }

  const currentPrice = getAssociationMembershipTypeCurrentPrice(
    associationMembershipType,
    contractStartDate,
  );

  if (!currentPrice) {
    return "";
  }

  return " " + formatCurrency(currentPrice.priceAsFloat) + " / Monat";
}
