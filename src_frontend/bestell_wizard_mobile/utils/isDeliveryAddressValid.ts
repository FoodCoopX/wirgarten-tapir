import { DeliveryAddressRequest } from "../../api-client";

export function isDeliveryAddressValid(
  deliveryAddress: DeliveryAddressRequest,
) {
  if (deliveryAddress.sameAsBillingAddress) {
    return true;
  }

  return [
    deliveryAddress.street,
    deliveryAddress.postcode,
    deliveryAddress.city,
  ].every((value) => (value ?? "").trim().length > 0);
}
