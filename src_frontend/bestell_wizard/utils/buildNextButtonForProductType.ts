import { isProductTypeOrdered } from "./isProductTypeOrdered.ts";
import { PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { NextButtonParameters } from "../types/NextButtonParameters.ts";

export function buildNextButtonParametersForProductType(
  productType: PublicProductType,
  shoppingCart: ShoppingCart,
  checkingCapacities: boolean,
): NextButtonParameters {
  if (checkingCapacities) {
    return {
      disabled: false,
      loading: true,
      text: "Kapazitäten werden geprüft...",
      icon: "unused_because_loading",
    };
  }

  if (isProductTypeOrdered(productType, shoppingCart)) {
    return {
      disabled: false,
      loading: false,
      text: productType.name + " zur Bestellung hinzufügen",
      icon: "add_shopping_cart",
    };
  }

  if (productType.mustBeSubscribedTo) {
    return {
      disabled: true,
      loading: false,
      text: productType.name + " müssen bestellt werden",
      icon: "shopping_cart_off",
    };
  }

  return {
    disabled: false,
    loading: false,
    text: "Ohne " + productType.name + " weitergehen",
    icon: "shopping_cart_off",
  };
}
