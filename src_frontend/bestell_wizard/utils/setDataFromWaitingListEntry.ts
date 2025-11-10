import { PublicPickupLocation, type PublicProductType, WaitingListEntryDetails } from "../../api-client";
import { BestellWizardStep } from "../types/BestellWizardStep.ts";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { PersonalData } from "../types/PersonalData.ts";
import { buildEmptyShoppingCart } from "./buildEmptyShoppingCart.ts";
import { sortProductTypes } from "./sortProductTypes.ts";

export function setDataFromWaitingListEntry(
  waitingListEntryDetails: WaitingListEntryDetails,
  setCurrentStep: (step: string) => void,
  steps: (string | BestellWizardStep)[],
  settings: BestellWizardSettings,
  setSelectedProductTypes: (types: PublicProductType[]) => void,
  setShoppingCartOrder: (order: ShoppingCart) => void,
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void,
  setPersonalData: (data: PersonalData) => void,
  setSelectedNumberOfCoopShares: (num: number) => void,
) {
  if (
    waitingListEntryDetails.productWishes === undefined ||
    waitingListEntryDetails.productWishes.length === 0
  ) {
    setCurrentStep(steps.length > 0 ? steps[0] : "intro");
  } else {
    setShoppingCartOrder(
      buildShoppingCart(
        settings,
        waitingListEntryDetails,
        setSelectedProductTypes,
      ),
    );
  }

  if (
    waitingListEntryDetails.pickupLocationWishes !== undefined &&
    waitingListEntryDetails.pickupLocationWishes.length > 0 &&
    settings.pickupLocations.length > 0
  ) {
    const pickupLocation = settings.pickupLocations.find(
      (pl) =>
        pl.id ===
        waitingListEntryDetails.pickupLocationWishes![0].pickupLocation.id,
    );
    setSelectedPickupLocations([pickupLocation!]);
  }

  setPersonalData({
    firstName: waitingListEntryDetails.firstName,
    lastName: waitingListEntryDetails.lastName,
    email: waitingListEntryDetails.email,
    phoneNumber: waitingListEntryDetails.phoneNumber,
    street: waitingListEntryDetails.street,
    street2: waitingListEntryDetails.street2,
    postcode: waitingListEntryDetails.postcode,
    city: waitingListEntryDetails.city,
    country: "de",
    iban: waitingListEntryDetails.iban ?? "",
    accountOwner: waitingListEntryDetails.accountOwner ?? "",
    paymentRhythm: waitingListEntryDetails.paymentRhythm ?? "",
  });

  setSelectedNumberOfCoopShares(waitingListEntryDetails.numberOfCoopShares);
}

function buildShoppingCart(
  settings: BestellWizardSettings,
  waitingListEntryDetails: WaitingListEntryDetails,
  setSelectedProductTypes: (types: PublicProductType[]) => void,
) {
  const newShoppingCart = buildEmptyShoppingCart(settings.productTypes);
  const selectedProductTypes = new Set<PublicProductType>();
  for (const wish of waitingListEntryDetails.productWishes ?? []) {
    newShoppingCart[wish.product.id!] = wish.quantity;
    const publicProductType = settings.productTypes.find(
      (pt) => pt.id === wish.product.type.id,
    );
    if (publicProductType) {
      selectedProductTypes.add(publicProductType);
    }
  }
  setSelectedProductTypes(sortProductTypes([...selectedProductTypes]));
  return newShoppingCart;
}
