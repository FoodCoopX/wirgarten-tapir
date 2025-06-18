import { useApi } from "../../hooks/useApi.ts";
import {
  CoreApi,
  PickupLocationsApi,
  PublicPickupLocation,
  PublicProductType,
  SubscriptionsApi,
} from "../../api-client";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { sortProductTypes } from "./sortProductTypes.ts";

export function loadBaseBestellWizardData(
  setTheme: (theme: TapirTheme) => void,
  setPublicProductTypes: (productTypes: PublicProductType[]) => void,
  setPickupLocations: (pickupLocations: PublicPickupLocation[]) => void,
) {
  const coreApi = useApi(CoreApi, "unused");
  const subscriptionsApi = useApi(SubscriptionsApi, "unused");
  const pickupLocationApi = useApi(PickupLocationsApi, "unused");

  coreApi
    .coreApiGetThemeRetrieve()
    .then((themeAsString) => {
      setTheme(themeAsString as TapirTheme);
    })
    .catch(handleRequestError);

  subscriptionsApi
    .subscriptionsPublicProductTypesList()
    .then((types) => {
      setPublicProductTypes(sortProductTypes(types));
    })
    .catch(handleRequestError);

  pickupLocationApi
    .pickupLocationsPublicPickupLocationsList()
    .then((pickupLocations) => {
      pickupLocations.sort((a, b) => {
        return a.name.localeCompare(b.name);
      });
      setPickupLocations(pickupLocations);
    })
    .catch(handleRequestError);
}
