import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { getProductTypeByProductId } from "./getProductTypeByProductId.ts";

export function getShoppingCartWithoutAssociationMembership(
  shoppingCart: ShoppingCart,
  settings: BestellWizardSettings,
): ShoppingCart {
  return Object.fromEntries(
    Object.entries(shoppingCart).filter(
      ([productId, _]) =>
        !getProductTypeByProductId(productId, settings)
          ?.isAssociationMembership,
    ),
  );
}
