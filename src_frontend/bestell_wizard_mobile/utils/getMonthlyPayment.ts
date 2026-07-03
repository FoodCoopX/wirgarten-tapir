import { AssociationMembershipType, PublicProductType } from "../../api-client";
import { getAssociationMembershipTypeCurrentPrice } from "../../association_memberships_config/getAssociationMembershipTypeCurrentPrice.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { getProductById } from "./getProductByIdGlobal.ts";

export function getMonthlyPayment(
  solidarityContribution: number,
  shoppingCart: ShoppingCart,
  settings: BestellWizardSettings,
  productTypesInWaitingList: Set<PublicProductType>,
  associationMembershipType: AssociationMembershipType | undefined,
  contractStartDate: Date,
) {
  let monthlyPayment = solidarityContribution;
  for (const [productId, quantity] of Object.entries(shoppingCart)) {
    for (const productType of settings.productTypes) {
      if (productTypesInWaitingList.has(productType)) {
        continue;
      }
      const product = getProductById(productType, productId);
      if (!product) {
        continue;
      }
      monthlyPayment += product.price * quantity;
    }
  }

  if (associationMembershipType) {
    const currentPrice = getAssociationMembershipTypeCurrentPrice(
      associationMembershipType,
      contractStartDate,
    );
    if (currentPrice) {
      monthlyPayment += currentPrice.priceAsFloat;
    }
  }

  return monthlyPayment;
}
