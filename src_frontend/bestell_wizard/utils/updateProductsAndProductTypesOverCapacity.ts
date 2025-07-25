import { handleRequestError } from "../../utils/handleRequestError.ts";
import { useApi } from "../../hooks/useApi.ts";
import { SubscriptionsApi } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";

export function updateProductsAndProductTypesOverCapacity(
  shoppingCart: ShoppingCart,
  setProductIdsOverCapacity: (ids: string[]) => void,
  setProductTypeIdsOverCapacity: (ids: string[]) => void,
  setCheckingCapacities: (enabled: boolean) => void,
) {
  const subscriptionsApi = useApi(SubscriptionsApi, getCsrfToken());

  setCheckingCapacities(true);

  subscriptionsApi
    .subscriptionsApiBestellWizardCapacityCheckCreate({
      bestellWizardCapacityCheckRequestRequest: {
        shoppingCart: shoppingCart,
      },
    })
    .then((response) => {
      setProductIdsOverCapacity(response.idsOfProductsOverCapacity);
      setProductTypeIdsOverCapacity(response.idsOfProductTypesOverCapacity);
    })
    .catch(handleRequestError)
    .finally(() => setCheckingCapacities(false));
}
