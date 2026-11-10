import React, { useEffect, useMemo, useState } from "react";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import Step5CPickupLocationList from "../components/Step5CPickupLocationList.tsx";
import Step5CPickupLocationWishes from "../components/Step5CPickupLocationWishes.tsx";
import { getPickupLocationsForDeliveryMode } from "../utils/getPickupLocationsForDeliveryMode.ts";
import { shouldShowPickupLocationWishes } from "../utils/shouldShowPickupLocationWishes.ts";

interface Step5DHomeDeliveryChoiceProps {
  settings: BestellWizardSettings;
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsCapacityCheckLoading: boolean;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  goToNextStep: () => void;
  firstDeliveryDatesByPickupLocationAndProductType: {
    [key: string]: { [key: string]: Date };
  };
  stepActive: boolean;
  productTypesInWaitingList: Set<PublicProductType>;
  shoppingCart: ShoppingCart;
  productTypeIdsOverCapacity: string[];
  productIdsOverCapacity: string[];
  changesDisabled: boolean;
}

const Step5DHomeDeliveryChoice: React.FC<Step5DHomeDeliveryChoiceProps> = ({
  settings,
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocationsCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  goToNextStep,
  firstDeliveryDatesByPickupLocationAndProductType,
  stepActive,
  productTypesInWaitingList,
  shoppingCart,
  productTypeIdsOverCapacity,
  productIdsOverCapacity,
  changesDisabled,
}) => {
  const [showValidation, setShowValidation] = useState(false);

  const homeDeliveryLocations = useMemo(
    () =>
      getPickupLocationsForDeliveryMode(
        settings.pickupLocations,
        "home_delivery",
      ),
    [settings.pickupLocations],
  );

  useEffect(() => {
    if (!stepActive) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [stepActive]);

  function validate() {
    setShowValidation(true);

    if (selectedPickupLocations.length === 0) {
      return;
    }

    goToNextStep();
  }

  return (
    <>
      <div
        className={"d-flex flex-column gap-2"}
        style={{ width: "100%", flexGrow: 1, overflow: "auto" }}
      >
        <Step5CPickupLocationList
          pickupLocations={homeDeliveryLocations}
          selectedPickupLocations={selectedPickupLocations}
          setSelectedPickupLocations={setSelectedPickupLocations}
          pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
          pickupLocationsCapacityCheckLoading={
            pickupLocationsCapacityCheckLoading
          }
          waitingListLinkConfirmationModeEnabled={false}
          tabIsActive={stepActive}
          firstDeliveryDatesByPickupLocationAndProductType={
            firstDeliveryDatesByPickupLocationAndProductType
          }
          productTypesInWaitingList={productTypesInWaitingList}
          shoppingCart={shoppingCart}
          changesDisabled={changesDisabled}
          isHomeDelivery={true}
        />
        {homeDeliveryLocations.length > 1 &&
          shouldShowPickupLocationWishes(
            changesDisabled,
            shoppingCart,
            productTypeIdsOverCapacity,
            productIdsOverCapacity,
            settings,
            selectedPickupLocations,
            pickupLocationsWithCapacityFull,
          ) && (
            <Step5CPickupLocationWishes
              pickupLocations={homeDeliveryLocations}
              selectedPickupLocations={selectedPickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            />
          )}
      </div>
      <NextStepButton
        onClick={validate}
        text={
          showValidation && selectedPickupLocations.length === 0
            ? "Noch keine Hauslieferung ausgewählt"
            : undefined
        }
        showError={showValidation && selectedPickupLocations.length === 0}
        stepActive={stepActive}
      />
    </>
  );
};

export default Step5DHomeDeliveryChoice;
