import React, { useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ButtonGroup, Carousel, ToggleButton } from "react-bootstrap";
import Step5BPickupLocationList from "../components/Step5BPickupLocationList.tsx";
import { PublicPickupLocation } from "../../api-client";
import Step5BPickupLocationMap from "../components/Step5BPickupLocationMap.tsx";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";

interface Step5BPickupLocationChoiceProps {
  settings: BestellWizardSettings;
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  goToNextStep: () => void;
  stepIsActive: boolean;
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
}) => {
  const tabs: PickupLocationTab[] = ["wishes", "list", "map"];
  const [currentTab, setCurrentTab] = useState<PickupLocationTab>("map");

  return (
    <>
      <ButtonGroup style={{ width: "90%" }}>
        {tabs.map((tab) => (
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
        style={{ width: "100%" }}
      >
        <Carousel.Item>
          <div className={"text-center"} style={{ height: "50dvh" }}>
            <p>Tab Wünsche</p>
            <p>
              Hier könnten im Wartelistemodus weiter Wünsche hinzugefügt werden
              und deren Reihenfolge angepasst werden.
            </p>
            <p>
              Außerhalb der Wartelistemodus würde dieses Tab nicht angezeigt
              werden.
            </p>
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
          />
        </Carousel.Item>
        <Carousel.Item>
          <Step5BPickupLocationMap
            pickupLocations={settings.pickupLocations}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            tabIsActive={currentTab === "map" && stepIsActive}
          />
        </Carousel.Item>
      </Carousel>
      <NextStepButton
        onClick={goToNextStep}
        disabled={selectedPickupLocations.length === 0}
      />
    </>
  );
};

export default Step5BPickupLocationChoice;
