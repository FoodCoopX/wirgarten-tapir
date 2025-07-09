import { PublicPickupLocation, SubscriptionsApi } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

export function fetchFirstDeliveryDates(
  pickupLocations: PublicPickupLocation[],
  shoppingCart: ShoppingCart,
  setFirstDeliveryDatesByProductType: (map: { [key: string]: Date }) => void,
) {
  if (pickupLocations.length === 0) {
    return;
  }
  const subscriptionsApi = useApi(SubscriptionsApi, "unused");

  subscriptionsApi
    .subscriptionsApiBestellWizardDeliveryDatesCreate({
      bestellWizardDeliveryDatesForOrderRequestRequest: {
        pickupLocationId: pickupLocations[0].id!,
        shoppingCart: shoppingCart,
      },
    })
    .then((response) => {
      const entries = Object.entries(
        response.productTypeIdToNextDeliveryDateMap,
      );

      setFirstDeliveryDatesByProductType(
        Object.fromEntries(
          entries.map(([productId, dateAsString]) => [
            productId,
            new Date(dateAsString as unknown as string), //The generated client say that the values are Dates, but they are actually strings
          ]),
        ),
      );
    })
    .catch(handleRequestError);
}
