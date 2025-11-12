import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ButtonGroup, Carousel, ToggleButton } from "react-bootstrap";
import Step5BPickupLocationList from "../components/Step5BPickupLocationList.tsx";
import { PublicPickupLocation } from "../../api-client";
import Step5BPickupLocationMap from "../components/Step5BPickupLocationMap.tsx";
import StepTitle from "../components/StepTitle.tsx";

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
      <div
        style={{ height: "80dvh", display: "flex", flexDirection: "column" }}
        className={"d-flex flex-column gap-2 mx-4"}
      >
        <StepTitle title={"An welcher Verteilstation möchtest du abholen?"} />
        <h4 className={"mx-4 mb-0 text-center"}></h4>
        <ButtonGroup>
          {tabs.map((tab) => (
            <ToggleButton
              key={tab}
              id={tab}
              value={tab}
              type={"radio"}
              variant={"outline-secondary"}
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
            <div className={"text-center"}>
              <p>Tab Wünsche</p>
              <p>
                Hier könnten im Wartelistemodus weiter Wünsche hinzugefügt
                werden und deren Reihenfolge angepasst werden.
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
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
            disabled={selectedPickupLocations.length === 0}
            icon={"keyboard_arrow_down"}
          />
        </div>
      </div>
    </>
  );
};

export default Step5BPickupLocationChoice;
