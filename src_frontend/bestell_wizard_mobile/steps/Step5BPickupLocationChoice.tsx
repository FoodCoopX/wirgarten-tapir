import React, { useEffect, useRef, useMemo, useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ButtonGroup, Carousel, ToggleButton } from "react-bootstrap";
import Step5BPickupLocationList from "../components/Step5BPickupLocationList.tsx";
import { PublicPickupLocation, type PublicProductType } from "../../api-client";
import Step5BPickupLocationMap from "../components/Step5BPickupLocationMap.tsx";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { CarouselRef } from "react-bootstrap/Carousel";
import { MapRef } from "react-leaflet/MapContainer";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import DeliveryDayTabs from "../../components/DeliveryDayTabs.tsx";
import {
  ALL_PICKUP_LOCATION_TABS,
  PickupLocationTab,
} from "../types/PickupLocationTab.ts";
import Step5BPickupLocationWishes from "../components/Step5BPickupLocationWishes.tsx";
import { wouldTheOrderFitTheProductCapacities } from "../utils/wouldTheOrderFitTheProductCapacities.ts";

interface Step5BPickupLocationChoiceProps {
  settings: BestellWizardSettings;
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  goToNextStep: () => void;
  stepIsActive: boolean;
  firstDeliveryDatesByPickupLocationAndProductType: {
    [key: string]: { [key: string]: Date };
  };
  active: boolean;
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

const Step5BPickupLocationChoice: React.FC<Step5BPickupLocationChoiceProps> = ({
  settings,
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocationsWithCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  goToNextStep,
  stepIsActive,
  firstDeliveryDatesByPickupLocationAndProductType,
  active,
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
  const [selectedDeliveryDay, setSelectedDeliveryDay] = useState<number | null>(null);


  const availableDeliveryDays = useMemo((): number[] => {
    const days = new Set(
      settings.pickupLocations
        .map((loc) => Number(loc.deliveryDay))
        .filter((day) => !isNaN(day))
    );
    return Array.from(days).sort();
  }, [settings.pickupLocations]);

  const filteredPickupLocations = useMemo(() => {
    if (selectedDeliveryDay === null) {
      return settings.pickupLocations;
    }
    return settings.pickupLocations.filter(
      (loc) => Number(loc.deliveryDay) === selectedDeliveryDay
    );
  }, [settings.pickupLocations, selectedDeliveryDay]);

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

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
    if (changesDisabled) {
      return false;
    }

    if (
      !wouldTheOrderFitTheProductCapacities(
        shoppingCart,
        productTypeIdsOverCapacity,
        productIdsOverCapacity,
        settings,
      )
    ) {
      return true;
    }

    switch (selectedPickupLocations.length) {
      case 0:
        return false;
      case 1:
        return pickupLocationsWithCapacityFull.has(selectedPickupLocations[0]);
      default:
        return true;
    }
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
        onSelectDay={setSelectedDeliveryDay}
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
            <Step5BPickupLocationMap
              pickupLocations={filteredPickupLocations}
              selectedPickupLocations={selectedPickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              stepIsActive={active}
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
        <Carousel.Item>
          <Step5BPickupLocationList
            pickupLocations={filteredPickupLocations}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            pickupLocationsWithCapacityCheckLoading={
              pickupLocationsWithCapacityCheckLoading
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
            <Step5BPickupLocationWishes
              settings={settings}
              selectedPickupLocations={selectedPickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
              shoppingCart={shoppingCart}
              productTypesInWaitingList={productTypesInWaitingList}
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
      />
    </>
  );
};

export default Step5BPickupLocationChoice;
