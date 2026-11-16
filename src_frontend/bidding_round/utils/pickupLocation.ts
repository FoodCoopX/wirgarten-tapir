import { RoundTexts } from "../../api-client";

export const PICKUP_LOCATION_FALLBACK_TITLE = "Abholort";
export const DELIVERY_CHARGE_LABEL = "Lieferzuschlag pro Monat";

export function getPickupLocationTitle(texts: RoundTexts): string {
  return texts.pickupLocationTitle || PICKUP_LOCATION_FALLBACK_TITLE;
}
