import type { PublicPickupLocation, PublicProductType } from "../../api-client";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { isProductOrdered } from "./isProductOrdered.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

export function updateWaitingList(
  selectedPickupLocations: PublicPickupLocation[],
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>,
  settings: BestellWizardSettings,
  shoppingCart: ShoppingCart,
  productTypeIdsOverCapacity: string[],
  productIdsOverCapacity: string[],
  setProductTypesInWaitingList: (set: Set<PublicProductType>) => void,
) {
  const newProductsInWaitingList = new Set<PublicProductType>();

  const pickupLocationForcesWaitingList =
    doesPickupLocationSelectionForceWaitingListForDeliveredProducts(
      selectedPickupLocations,
      pickupLocationsWithCapacityFull,
    );

  for (const productType of settings.productTypes) {
    if (!isProductTypeOrdered(productType, shoppingCart)) {
      continue;
    }

    if (productTypeIdsOverCapacity.includes(productType.id!)) {
      newProductsInWaitingList.add(productType);
    }

    if (pickupLocationForcesWaitingList && !productType.noDelivery) {
      newProductsInWaitingList.add(productType);
    }

    for (const product of productType.products) {
      if (
        isProductOrdered(product, shoppingCart) &&
        productIdsOverCapacity.includes(product.id!)
      ) {
        newProductsInWaitingList.add(productType);
      }
    }
  }

  setProductTypesInWaitingList(newProductsInWaitingList);
}

function doesPickupLocationSelectionForceWaitingListForDeliveredProducts(
  selectedPickupLocations: PublicPickupLocation[],
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>,
) {
  if (selectedPickupLocations.length === 0) {
    return false;
  }

  const pickupLocationsWithEnoughCapacity = selectedPickupLocations.filter(
    (pickupLocation) => !pickupLocationsWithCapacityFull.has(pickupLocation),
  );

  return pickupLocationsWithEnoughCapacity.length === 0;
}
