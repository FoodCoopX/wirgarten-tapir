import {
  BestellWizardGrowingPeriodChoice,
  PublicPickupLocation,
} from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { buildEmptyShoppingCart } from "./buildEmptyShoppingCart.ts";

export function onGrowingPeriodSelected(
  growingPeriod: BestellWizardGrowingPeriodChoice,
  shoppingCart: ShoppingCart,
  setSelectedGrowingPeriod: (
    growingPeriod: BestellWizardGrowingPeriodChoice,
  ) => void,
  setSelectedPickupLocations: (pickupLocations: PublicPickupLocation[]) => void,
  setShoppingCart: (shoppingCart: ShoppingCart) => void,
) {
  setSelectedGrowingPeriod(growingPeriod);
  setSelectedPickupLocations([]);

  const newShoppingCart = buildEmptyShoppingCart(growingPeriod.productTypes);
  for (const productId of Object.keys(newShoppingCart)) {
    newShoppingCart[productId] = shoppingCart[productId] ?? 0;
  }
  setShoppingCart(newShoppingCart);
}
