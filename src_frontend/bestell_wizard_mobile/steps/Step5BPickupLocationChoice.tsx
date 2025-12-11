import React, { useEffect, useRef, useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ButtonGroup, Carousel, ToggleButton } from "react-bootstrap";
import Step5BPickupLocationList from "../components/Step5BPickupLocationList.tsx";
import { PublicPickupLocation, type PublicProductType } from "../../api-client";
import Step5BPickupLocationMap from "../components/Step5BPickupLocationMap.tsx";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { CarouselRef } from "react-bootstrap/Carousel";
import { MapRef } from "react-leaflet/MapContainer";
import { isAtLeastOneOrderedProductWithDelivery } from "../../bestell_wizard/utils/isAtLeastOneOrderedProductWithDelivery.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import {
  ALL_PICKUP_LOCATION_TABS,
  PickupLocationTab,
} from "../types/PickupLocationTab.ts";
import Step5BPickupLocationWishes from "../components/Step5BPickupLocationWishes.tsx";
import { buildFilteredShoppingCart } from "../../bestell_wizard/utils/buildFilteredShoppingCart.ts";

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
  setProductTypesInWaitingList: (set: Set<PublicProductType>) => void;
  shoppingCart: ShoppingCart;
  currentTab: PickupLocationTab;
  setCurrentTab: (tab: PickupLocationTab) => void;
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
  setProductTypesInWaitingList,
  shoppingCart,
  currentTab,
  setCurrentTab,
}) => {
  const [showValidation, setShowValidation] = useState(false);
  const carouselRef = useRef<CarouselRef>(null);
  const [mapRef, setMapRef] = useState<MapRef>(null);

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
    return !isAtLeastOneOrderedProductWithDelivery(
      buildFilteredShoppingCart(shoppingCart, false, productTypesInWaitingList),
      settings.productTypes,
    );
  }

  return (
    <>
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
            {tab === "wishes" ? "Wünsche" : tab === "map" ? "Karte" : "Liste"}
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
              pickupLocations={settings.pickupLocations}
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
            />
          </div>
        </Carousel.Item>
        <Carousel.Item>
          <Step5BPickupLocationList
            pickupLocations={settings.pickupLocations}
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
        text={
          showValidation && selectedPickupLocations.length === 0
            ? "Noch kein Verteilstation ausgewählt"
            : undefined
        }
        showError={showValidation && selectedPickupLocations.length === 0}
      />
    </>
  );
};

export default Step5BPickupLocationChoice;
