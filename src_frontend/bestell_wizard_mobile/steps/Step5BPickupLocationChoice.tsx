import React, { useEffect, useRef, useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ButtonGroup, Carousel, Form, ToggleButton } from "react-bootstrap";
import Step5BPickupLocationList from "../components/Step5BPickupLocationList.tsx";
import { PublicPickupLocation, type PublicProductType } from "../../api-client";
import Step5BPickupLocationMap from "../components/Step5BPickupLocationMap.tsx";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { CarouselRef } from "react-bootstrap/Carousel";
import { MapRef } from "react-leaflet/MapContainer";
import PickupLocationWaitingListModal from "../../bestell_wizard/components/PickupLocationWaitingListModal.tsx";
import { isAtLeastOneOrderedProductWithDelivery } from "../../bestell_wizard/utils/isAtLeastOneOrderedProductWithDelivery.ts";
import { buildFilteredShoppingCart } from "../../bestell_wizard/utils/buildFilteredShoppingCart.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import TapirButton from "../../components/TapirButton.tsx";

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
}

type PickupLocationTab = "wishes" | "list" | "map";

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
}) => {
  const tabs: PickupLocationTab[] = ["map", "list", "wishes"];
  const [showValidation, setShowValidation] = useState(false);
  const [currentTab, setCurrentTab] = useState<PickupLocationTab>("map");
  const carouselRef = useRef<CarouselRef>(null);
  const [mapRef, setMapRef] = useState<MapRef>(null);
  const [waitingListModalOpen, setWaitingListModalOpen] = useState(false);

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

    if (shouldOpenWaitingListModal()) {
      setWaitingListModalOpen(true);
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

  function shouldOpenWaitingListModal() {
    if (
      !isAtLeastOneOrderedProductWithDelivery(
        buildFilteredShoppingCart(
          shoppingCart,
          false,
          productTypesInWaitingList,
        ),
        settings.productTypes,
      )
    ) {
      return false;
    }

    return pickupLocationsWithCapacityFull.has(selectedPickupLocations[0]);
  }

  function setPickupLocationAtIndex(
    pickupLocation: PublicPickupLocation,
    index: number,
  ) {
    selectedPickupLocations[index] = pickupLocation;
    setSelectedPickupLocations([...selectedPickupLocations]);
  }

  return (
    <>
      <ButtonGroup style={{ width: "100%" }}>
        {tabs
          .filter(
            (tab) => tab !== "wishes" || productTypesInWaitingList.size > 0,
          )
          .map((tab) => (
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
        activeIndex={tabs.indexOf(currentTab)}
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
              tabIsActive={currentTab === "map" && stepIsActive}
              mapRef={mapRef}
              setMapRef={setMapRef}
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
              firstDeliveryDatesByPickupLocationAndProductType={
                firstDeliveryDatesByPickupLocationAndProductType
              }
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
          />
        </Carousel.Item>
        {productTypesInWaitingList.size > 0 && (
          <Carousel.Item>
            <div className={"d-flex flex-column gap-2 align-items-center"}>
              {selectedPickupLocations.map((selectedPickupLocation, index) => (
                <Form.Group key={index}>
                  <Form.Label>{index + 1}. Wunsch</Form.Label>
                  <div className="d-flex flex-row gap-2">
                    <Form.Select
                      style={{ maxWidth: "200px" }}
                      onChange={(event) =>
                        setPickupLocationAtIndex(
                          settings.pickupLocations.find(
                            (pickupLocation) =>
                              pickupLocation.id === event.target.value,
                          )!,
                          index,
                        )
                      }
                      value={selectedPickupLocation.id}
                    >
                      {settings.pickupLocations.map((pickupLocation) => (
                        <option
                          key={pickupLocation.id}
                          value={pickupLocation.id}
                        >
                          {pickupLocation.name}
                        </option>
                      ))}
                    </Form.Select>
                    <TapirButton
                      variant={"outline-danger"}
                      size={"sm"}
                      icon={"delete"}
                      onClick={() =>
                        setSelectedPickupLocations(
                          selectedPickupLocations.filter(
                            (_, index2) => index2 !== index,
                          ),
                        )
                      }
                    />
                  </div>
                </Form.Group>
              ))}
              {selectedPickupLocations.length < 3 && (
                <TapirButton
                  variant={BUTTON_VARIANT}
                  text={"Weitere Wunsch hinzufügen"}
                  icon={"add_circle"}
                  onClick={() =>
                    setSelectedPickupLocations([
                      ...selectedPickupLocations,
                      settings.pickupLocations[0],
                    ])
                  }
                />
              )}
            </div>
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
      <PickupLocationWaitingListModal
        show={waitingListModalOpen}
        onHide={() => setWaitingListModalOpen(false)}
        confirmEnableWaitingListMode={() => {
          setWaitingListModalOpen(false);
          setProductTypesInWaitingList(
            new Set(
              settings.productTypes.filter(
                (productType) => !productType.noDelivery,
              ),
            ),
          );
          setCurrentTab("wishes");
        }}
      />
    </>
  );
};

export default Step5BPickupLocationChoice;
