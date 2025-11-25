import React, { useEffect } from "react";
import { PublicPickupLocation } from "../../api-client";
import { ListGroup, ListGroupItem, Spinner } from "react-bootstrap";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../../bestell_wizard/utils/formatOpeningTimes.ts";
import { getFirstDelivery } from "../utils/getFirstDelivery.ts";

interface Step5BPickupLocationListProps {
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  waitingListLinkConfirmationModeEnabled: boolean;
  tabIsActive: boolean;
  firstDeliveryDatesByPickupLocationAndProductType: {
    [key: string]: { [key: string]: Date };
  };
}

const Step5BPickupLocationList: React.FC<Step5BPickupLocationListProps> = ({
  pickupLocations,
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocationsWithCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  waitingListLinkConfirmationModeEnabled,
  tabIsActive,
  firstDeliveryDatesByPickupLocationAndProductType,
}) => {
  function getClassForPickupLocationListItem(
    pickupLocation: PublicPickupLocation,
  ) {
    if (selectedPickupLocations.includes(pickupLocation)) {
      return "active";
    }

    return "";
  }

  function buildCapacityIndicator(pickupLocation: PublicPickupLocation) {
    if (waitingListLinkConfirmationModeEnabled) {
      return;
    }

    if (pickupLocationsWithCapacityCheckLoading.has(pickupLocation)) {
      return <Spinner size={"sm"} />;
    }

    if (pickupLocationsWithCapacityFull.has(pickupLocation)) {
      return <span className={"text-danger"}>Ausgelastet</span>;
    }

    let dateAsString = getFirstDelivery(
      pickupLocation.id!,
      firstDeliveryDatesByPickupLocationAndProductType,
    );
    return <span className={"text-success"}>{dateAsString}</span>;
  }

  useEffect(() => {
    if (tabIsActive && selectedPickupLocations.length > 0) {
      setTimeout(() => {
        const elem = document.getElementById(selectedPickupLocations[0].id!);
        elem?.scrollIntoView();
      }, 10);
    }
  }, [tabIsActive]);

  return (
    <ListGroup style={{ maxHeight: "50dvh", overflow: "scroll" }}>
      {pickupLocations.map((pickupLocation) => (
        <ListGroupItem
          key={pickupLocation.id}
          style={{
            cursor: "pointer",
            lineHeight: "1.1rem",
          }}
          onClick={() => setSelectedPickupLocations([pickupLocation])}
          className={getClassForPickupLocationListItem(pickupLocation)}
          id={pickupLocation.id}
        >
          <small style={{ lineHeight: "0" }}>
            <strong>{pickupLocation.name}</strong>
            <br />
            {buildCapacityIndicator(pickupLocation)}
            <br />
            <small>
              {formatAddress(
                pickupLocation.street,
                pickupLocation.street2,
                pickupLocation.postcode,
                pickupLocation.city,
              )}
            </small>
            <br />
            <small>{formatOpeningTimes(pickupLocation)}</small>
          </small>
        </ListGroupItem>
      ))}
    </ListGroup>
  );
};

export default Step5BPickupLocationList;
