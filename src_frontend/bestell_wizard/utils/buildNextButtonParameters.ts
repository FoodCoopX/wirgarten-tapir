import { isProductTypeOrdered } from "./isProductTypeOrdered.ts";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { NextButtonParameters } from "../types/NextButtonParameters.ts";
import { isPersonalDataValid } from "./isPersonalDataValid.ts";
import { PersonalData } from "../types/PersonalData.ts";

export function buildNextButtonParametersForProductType(
  publicProductTypes: PublicProductType[],
  shoppingCart: ShoppingCart,
  checkingCapacities: boolean,
  currentStep: string,
): NextButtonParameters {
  const productType = publicProductTypes.find(
    (productType) => productType.id === currentStep,
  );

  if (productType === undefined) {
    return {
      disabled: true,
      loading: false,
      icon: undefined,
      text: "Unknown step: " + currentStep,
    };
  }

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

export function buildNextButtonParametersForIntro(
  selectedProductTypes: PublicProductType[],
  investingMembership: boolean,
): NextButtonParameters {
  const atLeastOneProductSelected = selectedProductTypes.length > 0;

  let text = undefined;
  if (atLeastOneProductSelected) {
    text = "Weiter als aktives Mitglied";
  } else if (investingMembership) {
    text = "Weiter als Fördermitglied";
  } else if (!atLeastOneProductSelected && !investingMembership) {
    text = "Wähle mindestens eine Mitgliedschaft um weiter zu gehen";
  }

  return {
    disabled: !atLeastOneProductSelected && !investingMembership,
    loading: false,
    icon: undefined,
    text: text,
  };
}

export function buildNextButtonParametersForPickupLocation(
  selectedPickupLocations: PublicPickupLocation[],
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>,
): NextButtonParameters {
  return {
    disabled:
      selectedPickupLocations.length === 0 ||
      pickupLocationsWithCapacityCheckLoading.size > 0,
    icon: undefined,
    loading: pickupLocationsWithCapacityCheckLoading.size > 0,
    text:
      selectedPickupLocations.length === 0
        ? "Wähle dein Verteilstation aus um weiter zu gehen"
        : undefined,
  };
}

export function buildNextButtonParametersForCoopShares(
  statuteAccepted: boolean,
  selectedNumberOfCoopShares: number,
  minimumNumberOfShares: number,
  waitingListModeEnabled: boolean,
  studentStatusEnabled: boolean,
): NextButtonParameters {
  let text = undefined;

  if (studentStatusEnabled) {
    text = "Weiter als Student*in";
  }

  let disabled = false;
  if (!studentStatusEnabled) {
    disabled =
      (!statuteAccepted && !waitingListModeEnabled) ||
      minimumNumberOfShares > selectedNumberOfCoopShares;

    if (!statuteAccepted && !waitingListModeEnabled) {
      text = "Akzeptiere die Satzung um weiter zu gehen";
    }
    if (minimumNumberOfShares > selectedNumberOfCoopShares) {
      text =
        "Du muss mindestens " +
        minimumNumberOfShares +
        " Geno-Anteile zeichnen";
    }
  }

  return {
    disabled: disabled,
    icon: undefined,
    loading: false,
    text: text,
  };
}

export function buildNextButtonParametersForPersonalData(
  personalData: PersonalData,
  sepaAllowed: boolean,
  contractAccepted: boolean,
  waitingListModeEnabled: boolean,
): NextButtonParameters {
  let text = undefined;
  if (!isPersonalDataValid(personalData)) {
    text = "Vervollständige deine Daten um weiter zu gehen";
  }

  if (!waitingListModeEnabled) {
    if (!sepaAllowed) {
      text = "Ermächtige das SEPA-Mandat um weiter zu gehen";
    } else if (!contractAccepted) {
      text = "Akzeptiere die Vertragsgrundsätze um weiter zu gehen";
    }
  }

  let disabled;
  if (waitingListModeEnabled) {
    disabled = !isPersonalDataValid(personalData);
  } else {
    disabled =
      !isPersonalDataValid(personalData) || !sepaAllowed || !contractAccepted;
  }

  return {
    disabled: disabled,
    icon: undefined,
    loading: false,
    text: text,
  };
}
