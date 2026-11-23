import {
  BestellWizardGrowingPeriodChoice,
  PublicWaitingListEntryDetails,
} from "../../api-client";

export function getGrowingPeriodForWaitingListEntry(
  growingPeriodChoices: BestellWizardGrowingPeriodChoice[],
  waitingListEntryDetails: PublicWaitingListEntryDetails,
) {
  const wishedProductIds = (waitingListEntryDetails.productWishes ?? []).map(
    (productWish) => productWish.product.id,
  );

  return (
    growingPeriodChoices.find((growingPeriod) => {
      const productIds = growingPeriod.productTypes.flatMap((productType) =>
        productType.products.map((product) => product.id),
      );
      return wishedProductIds.every((productId) =>
        productIds.includes(productId),
      );
    }) ?? growingPeriodChoices[0]
  );
}
