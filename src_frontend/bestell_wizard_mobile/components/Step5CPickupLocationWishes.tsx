import "leaflet/dist/leaflet.css";
import React from "react";
import { Form } from "react-bootstrap";
import { PublicPickupLocation } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import "./map.css";

interface Step5CPickupLocationWishesProps {
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
}

const MAX_NUMBER_OF_WISHES = 3;

const Step5CPickupLocationWishes: React.FC<Step5CPickupLocationWishesProps> = ({
  pickupLocations,
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocationsWithCapacityFull,
}) => {
  function setPickupLocationAtIndex(
    pickupLocation: PublicPickupLocation,
    index: number,
  ) {
    selectedPickupLocations[index] = pickupLocation;

    setSelectedPickupLocations([...new Set(selectedPickupLocations)]);
  }

  function getOptions(index: number) {
    let options = pickupLocations;
    for (let i = 0; i < index; i++) {
      options = options.filter(
        (pickupLocation) => pickupLocation !== selectedPickupLocations[i],
      );
    }

    return options;
  }

  function getWishLabel(index: number) {
    let label = index + 1 + ". Wunsch";
    if (pickupLocationsWithCapacityFull.has(selectedPickupLocations[index])) {
      label += " (Warteliste-Eintrag)";
    } else {
      label += " (Beim Einstieg)";
    }

    return label;
  }

  const unselectedPickupLocations = pickupLocations.filter(
    (pickupLocation) => !selectedPickupLocations.includes(pickupLocation),
  );

  return (
    <div className={"d-flex flex-column gap-2 align-items-center"}>
      {selectedPickupLocations.map((selectedPickupLocation, index) => (
        <Form.Group key={selectedPickupLocation.id + "_" + index}>
          <Form.Label>{getWishLabel(index)}</Form.Label>
          <div className="d-flex flex-row gap-2">
            <Form.Select
              style={{ maxWidth: "200px" }}
              onChange={(event) =>
                setPickupLocationAtIndex(
                  pickupLocations.find(
                    (pickupLocation) =>
                      pickupLocation.id === event.target.value,
                  )!,
                  index,
                )
              }
              value={selectedPickupLocation.id}
            >
              {getOptions(index).map((pickupLocation) => (
                <option key={pickupLocation.id} value={pickupLocation.id}>
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
      {selectedPickupLocations.length < MAX_NUMBER_OF_WISHES &&
        unselectedPickupLocations.length > 0 && (
          <TapirButton
            variant={BUTTON_VARIANT}
            text={"Weiterer Wunsch"}
            icon={"add_circle"}
            onClick={() =>
              setSelectedPickupLocations([
                ...selectedPickupLocations,
                unselectedPickupLocations[0],
              ])
            }
          />
        )}
    </div>
  );
};

export default Step5CPickupLocationWishes;
