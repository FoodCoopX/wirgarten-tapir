import {
  ProductForCancellation,
  SolidarityContributionCancellationData,
} from "../../api-client";

export function negativeSolidarityCancellationIsRequired(
  subscribedProducts: ProductForCancellation[],
  selectedProducts: ProductForCancellation[],
  canCancelAssociationMembership: boolean,
  cancelAssociationMembershipSelected: boolean,
  solidarityContributionData?: SolidarityContributionCancellationData,
) {
  if (
    !solidarityContributionData?._exists ||
    !solidarityContributionData.isNegative
  ) {
    return false;
  }

  const allProductsSelected =
    selectedProducts.length === subscribedProducts.length;
  const somethingIsCancelled =
    selectedProducts.length > 0 || cancelAssociationMembershipSelected;
  const associationMembershipIsHandled =
    !canCancelAssociationMembership || cancelAssociationMembershipSelected;

  return (
    allProductsSelected &&
    somethingIsCancelled &&
    associationMembershipIsHandled
  );
}
