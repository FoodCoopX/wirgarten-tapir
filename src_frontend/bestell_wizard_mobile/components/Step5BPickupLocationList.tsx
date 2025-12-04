import React, { useEffect } from "react";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import { ListGroup, ListGroupItem, Spinner } from "react-bootstrap";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../../bestell_wizard/utils/formatOpeningTimes.ts";
import { getFirstDelivery } from "../utils/getFirstDelivery.ts";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import { buildFilteredShoppingCart } from "../../bestell_wizard/utils/buildFilteredShoppingCart.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

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
  productTypesInWaitingList: Set<PublicProductType>;
  shoppingCart: ShoppingCart;
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
  shoppingCart,
  productTypesInWaitingList,
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

    let freeCapacityText;
    if (
      isAtLeastOneProductOrdered(
        buildFilteredShoppingCart(
          shoppingCart,
          false,
          productTypesInWaitingList,
        ),
      )
    ) {
      freeCapacityText = getFirstDelivery(
        pickupLocation.id!,
        firstDeliveryDatesByPickupLocationAndProductType,
      );
    } else {
      freeCapacityText = "Kapazität frei";
    }

    return (
      <span
        className={
          selectedPickupLocations.includes(pickupLocation) ? "" : "text-success"
        }
      >
        {freeCapacityText}
      </span>
    );
  }

  useEffect(() => {
    if (tabIsActive && selectedPickupLocations.length > 0) {
      setTimeout(() => {
        const elem = document.getElementById(selectedPickupLocations[0].id!);
        elem?.scrollIntoView();
      }, 10);
    }
  }, [tabIsActive]);

  function sortPickupLocations(
    a: PublicPickupLocation,
    b: PublicPickupLocation,
  ) {
    if (
      pickupLocationsWithCapacityFull.has(a) &&
      !pickupLocationsWithCapacityFull.has(b)
    ) {
      return 1;
    }

    if (
      pickupLocationsWithCapacityFull.has(b) &&
      !pickupLocationsWithCapacityFull.has(a)
    ) {
      return -1;
    }

    return a.name.localeCompare(b.name);
  }

  return (
    <ListGroup style={{ maxHeight: "50dvh", overflow: "scroll" }}>
      {pickupLocations.sort(sortPickupLocations).map((pickupLocation) => (
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
