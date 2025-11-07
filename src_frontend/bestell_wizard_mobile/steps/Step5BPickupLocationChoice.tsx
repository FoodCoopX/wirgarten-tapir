import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ButtonGroup, Carousel, ToggleButton } from "react-bootstrap";
import Step5BPickupLocationList from "../Components/Step5BPickupLocationList.tsx";
import { PublicPickupLocation } from "../../api-client";
import Step5BPickupLocationMap from "../Components/Step5BPickupLocationMap.tsx";

interface Step5BPickupLocationChoiceProps {
  settings: BestellWizardSettings;
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  goToNextStep: () => void;
}

type PickupLocationTab = "wishes" | "list" | "map";

const Step5BPickupLocationChoice: React.FC<Step5BPickupLocationChoiceProps> = ({
  settings,
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocationsWithCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  goToNextStep,
}) => {
  const tabs: PickupLocationTab[] = ["wishes", "list", "map"];
  const [currentTab, setCurrentTab] = useState<PickupLocationTab>("list");

  return (
    <>
      <div
        style={{ height: "80vh", display: "flex", flexDirection: "column" }}
        className={"d-flex flex-column gap-2 mx-4"}
      >
        <h4 className={"mx-4 text-center"}>
          An welcher Verteilstation möchtest du abholen?
        </h4>
        <ButtonGroup className={"mt-2"}>
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
              tabIsActive={currentTab === "list"}
            />
          </Carousel.Item>
          <Carousel.Item>
            <Step5BPickupLocationMap
              pickupLocations={settings.pickupLocations}
              selectedPickupLocations={selectedPickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              tabIsActive={currentTab === "map"}
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
          />
        </div>
      </div>
    </>
  );
};

export default Step5BPickupLocationChoice;
