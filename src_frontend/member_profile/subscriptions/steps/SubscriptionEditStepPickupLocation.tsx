import React from "react";
import { Modal } from "react-bootstrap";
import PickupLocationSelector from "../../../bestell_wizard/components/PickupLocationSelector";
import { PublicPickupLocation } from "../../../api-client";
import TapirButton from "../../../components/TapirButton.tsx";
import PickupLocationWaitingListSelector
  from "../../../bestell_wizard/components/PickupLocationWaitingListSelector.tsx";

interface SubscriptionEditStepPickupLocationProps {
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  waitingListModeEnabled: boolean;
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  onBackClicked: () => void;
  onNextClicked: () => void;
}

const SubscriptionEditStepPickupLocation: React.FC<
  SubscriptionEditStepPickupLocationProps
> = ({
  pickupLocations,
  selectedPickupLocations,
  setSelectedPickupLocations,
  waitingListModeEnabled,
  pickupLocationsWithCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  onBackClicked,
  onNextClicked,
}) => {
  return (
    <>
      <Modal.Body style={{ maxHeight: "65vh", overflowY: "scroll" }}>
        {waitingListModeEnabled && (
          <PickupLocationWaitingListSelector
            pickupLocations={pickupLocations}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
          />
        )}
        <PickupLocationSelector
          pickupLocations={pickupLocations}
          selectedPickupLocations={selectedPickupLocations}
          setSelectedPickupLocations={setSelectedPickupLocations}
          waitingListModeEnabled={waitingListModeEnabled}
          pickupLocationsWithCapacityCheckLoading={
            pickupLocationsWithCapacityCheckLoading
          }
          pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
          waitingListLinkConfirmationModeEnabled={false}
        />
      </Modal.Body>
      <Modal.Footer>
        <div
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
          style={{ width: "100%" }}
        >
          <TapirButton
            variant={"outline-secondary"}
            icon={"chevron_left"}
            iconPosition={"left"}
            text={"Zurück"}
            onClick={onBackClicked}
          />
          <TapirButton
            variant={"outline-primary"}
            icon={"chevron_right"}
            text={
              selectedPickupLocations.length > 0
                ? "Weiter"
                : "Wähle deine Verteilstation aus um weiter zu gehen"
            }
            iconPosition={"right"}
            disabled={selectedPickupLocations.length === 0}
            loading={pickupLocationsWithCapacityCheckLoading.size > 0}
            onClick={onNextClicked}
          />
        </div>
      </Modal.Footer>
    </>
  );
};

export default SubscriptionEditStepPickupLocation;
