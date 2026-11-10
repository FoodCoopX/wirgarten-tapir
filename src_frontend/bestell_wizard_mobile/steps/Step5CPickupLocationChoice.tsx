import React, { useEffect, useMemo, useRef, useState } from "react";
import { ButtonGroup, Carousel, ToggleButton } from "react-bootstrap";
import { CarouselRef } from "react-bootstrap/Carousel";
import { MapRef } from "react-leaflet/MapContainer";
import { PublicPickupLocation, type PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import DeliveryDayTabs from "../../components/DeliveryDayTabs.tsx";
import { getUniqueDeliveryDays } from "../../utils/getUniqueDeliveryDays.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import Step5CPickupLocationList from "../components/Step5CPickupLocationList.tsx";
import Step5CPickupLocationMap from "../components/Step5CPickupLocationMap.tsx";
import Step5CPickupLocationWishes from "../components/Step5CPickupLocationWishes.tsx";
import {
  ALL_PICKUP_LOCATION_TABS,
  PickupLocationTab,
} from "../types/PickupLocationTab.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { getPickupLocationsForDeliveryMode } from "../utils/getPickupLocationsForDeliveryMode.ts";
import { shouldShowPickupLocationWishes } from "../utils/shouldShowPickupLocationWishes.ts";

interface Step5CPickupLocationChoiceProps {
  settings: BestellWizardSettings;
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsCapacityCheckLoading: boolean;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  goToNextStep: () => void;
  stepIsActive: boolean;
  firstDeliveryDatesByPickupLocationAndProductType: {
    [key: string]: { [key: string]: Date };
  };
  stepActive: boolean;
  productTypesInWaitingList: Set<PublicProductType>;
  shoppingCart: ShoppingCart;
  currentTab: PickupLocationTab;
  setCurrentTab: (tab: PickupLocationTab) => void;
  productTypeIdsOverCapacity: string[];
  productIdsOverCapacity: string[];
  isOrderStep: boolean;
  orderLoading: boolean;
  nextButtonTextOverride?: string;
  changesDisabled: boolean;
}

function getTabName(tab: PickupLocationTab) {
  switch (tab) {
    case "wishes":
      return "Wünsche";
    case "list":
      return "Liste";
    case "map":
      return "Karte";
  }
}

const Step5CPickupLocationChoice: React.FC<Step5CPickupLocationChoiceProps> = ({
  settings,
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocationsCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  goToNextStep,
  stepIsActive,
  firstDeliveryDatesByPickupLocationAndProductType,
  stepActive,
  productTypesInWaitingList,
  shoppingCart,
  currentTab,
  setCurrentTab,
  productIdsOverCapacity,
  productTypeIdsOverCapacity,
  isOrderStep,
  nextButtonTextOverride,
  orderLoading,
  changesDisabled,
}) => {
  const [showValidation, setShowValidation] = useState(false);
  const carouselRef = useRef<CarouselRef>(null);
  const [mapRef, setMapRef] = useState<MapRef>(null);
  const [selectedDeliveryDay, setSelectedDeliveryDay] = useState<number | null>(
    null,
  );

  const pickupLocations = useMemo(
    () => getPickupLocationsForDeliveryMode(settings.pickupLocations, "pickup"),
    [settings.pickupLocations],
  );

  const availableDeliveryDays = useMemo(
    () => getUniqueDeliveryDays(pickupLocations),
    [pickupLocations],
  );

  const filteredPickupLocations = useMemo(() => {
    if (selectedDeliveryDay === null) {
      return pickupLocations;
    }
    return pickupLocations.filter(
      (loc) => loc.deliveryDay === selectedDeliveryDay,
    );
  }, [pickupLocations, selectedDeliveryDay]);

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

  useEffect(() => {
    if (!carouselRef.current?.element) {
      return;
    }

    if (!mapRef) {
      return;
    }

    const resizeObserver = new ResizeObserver(() => {
      mapRef.invalidateSize();
    });
    resizeObserver.observe(carouselRef.current?.element);

    return () => resizeObserver.disconnect();
  }, [carouselRef, mapRef]);

  function showTabWishes() {
    return shouldShowPickupLocationWishes(
      changesDisabled,
      shoppingCart,
      productTypeIdsOverCapacity,
      productIdsOverCapacity,
      settings,
      selectedPickupLocations,
      pickupLocationsWithCapacityFull,
    );
  }

  function getNextButtonText() {
    if (showValidation && selectedPickupLocations.length === 0) {
      return "Noch kein Verteilstation ausgewählt";
    }

    if (nextButtonTextOverride) {
      return nextButtonTextOverride;
    }

    return undefined;
  }

  return (
    <>
      <DeliveryDayTabs
        availableDays={availableDeliveryDays}
        selectedDay={selectedDeliveryDay}
        onSelectDay={(day) => {
          setSelectedDeliveryDay(day);
          setSelectedPickupLocations([]);
        }}
      />
      <ButtonGroup style={{ width: "100%" }}>
        {ALL_PICKUP_LOCATION_TABS.filter(
          (tab) => tab !== "wishes" || showTabWishes(),
        ).map((tab) => (
          <ToggleButton
            key={tab}
            id={tab}
            value={tab}
            type={"radio"}
            variant={BUTTON_VARIANT}
            name={"tabs"}
            checked={currentTab === tab}
            onChange={(event) =>
              setCurrentTab(event.target.value as PickupLocationTab)
            }
            style={{ width: "100%" }}
          >
            {getTabName(tab)}
          </ToggleButton>
        ))}
      </ButtonGroup>
      <Carousel
        activeIndex={ALL_PICKUP_LOCATION_TABS.indexOf(currentTab)}
        indicators={false}
        controls={false}
        interval={null}
        touch={false}
        style={{ width: "100%", flexGrow: 1 }}
        ref={carouselRef}
        id={"pickup_location_carousel"}
      >
        <Carousel.Item style={{ position: "absolute", inset: 0 }}>
          <div style={{ position: "absolute", inset: 0 }}>
            <Step5CPickupLocationMap
              pickupLocations={filteredPickupLocations}
              selectedPickupLocations={selectedPickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              stepIsActive={stepActive}
              tabIsActive={currentTab === "map" && stepIsActive}
              mapRef={mapRef}
              setMapRef={setMapRef}
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
              firstDeliveryDatesByPickupLocationAndProductType={
                firstDeliveryDatesByPickupLocationAndProductType
              }
              productTypesInWaitingList={productTypesInWaitingList}
              shoppingCart={shoppingCart}
              settings={settings}
              productTypeIdsOverCapacity={productTypeIdsOverCapacity}
              productIdsOverCapacity={productIdsOverCapacity}
              changesDisabled={changesDisabled}
            />
          </div>
        </Carousel.Item>
        <Carousel.Item style={{ position: "absolute", inset: 0 }}>
          <Step5CPickupLocationList
            pickupLocations={filteredPickupLocations}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            pickupLocationsCapacityCheckLoading={
              pickupLocationsCapacityCheckLoading
            }
            waitingListLinkConfirmationModeEnabled={false}
            tabIsActive={currentTab === "list" && stepIsActive}
            firstDeliveryDatesByPickupLocationAndProductType={
              firstDeliveryDatesByPickupLocationAndProductType
            }
            productTypesInWaitingList={productTypesInWaitingList}
            shoppingCart={shoppingCart}
            changesDisabled={changesDisabled}
          />
        </Carousel.Item>
        {showTabWishes() && (
          <Carousel.Item>
            <Step5CPickupLocationWishes
              pickupLocations={pickupLocations}
              selectedPickupLocations={selectedPickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            />
          </Carousel.Item>
        )}
      </Carousel>
      <NextStepButton
        onClick={validate}
        text={getNextButtonText()}
        showError={showValidation && selectedPickupLocations.length === 0}
        loading={orderLoading}
        isOrderStep={isOrderStep}
        stepActive={stepActive}
      />
    </>
  );
};

export default Step5CPickupLocationChoice;
