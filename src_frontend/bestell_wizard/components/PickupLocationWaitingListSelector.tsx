import React from "react";
import { Col, Form, Row } from "react-bootstrap";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicPickupLocation } from "../../api-client";

interface PickupLocationWaitingListSelectorProps {
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (
    selectedPickupLocations: PublicPickupLocation[],
  ) => void;
  pickupLocations: PublicPickupLocation[];
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
}

const PickupLocationWaitingListSelector: React.FC<
  PickupLocationWaitingListSelectorProps
> = ({
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocations,
  pickupLocationsWithCapacityFull,
}) => {
  function setPickupLocationAtIndex(
    pickupLocation: PublicPickupLocation,
    index: number,
  ) {
    selectedPickupLocations[index] = pickupLocation;
    setSelectedPickupLocations([...selectedPickupLocations]);
  }

  function getPickupLocationsThatAreFull() {
    return pickupLocations.filter((pickupLocation) =>
      pickupLocationsWithCapacityFull.has(pickupLocation),
    );
  }

  function getNewWishLocation() {
    const pickupLocationsThatAreFull = getPickupLocationsThatAreFull();
    if (pickupLocationsThatAreFull.length > 0) {
      return pickupLocationsThatAreFull[0];
    }
    return pickupLocations[0];
  }

  return (
    <Row className={"mb-2"}>
      <Col>
        <div className={"d-flex flex-row gap-2"}>
          {selectedPickupLocations.map((selectedPickupLocation, index) => (
            <Form.Group key={index}>
              <Form.Label>{index + 1}. Wunsch</Form.Label>
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
                  {getPickupLocationsThatAreFull().map((pickupLocation) => (
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
          {selectedPickupLocations.length < 3 && (
            <div className={"d-flex flex-column justify-content-end"}>
              <TapirButton
                variant={"outline-primary"}
                text={"Weitere Wunsch hinzufügen"}
                icon={"add_circle"}
                onClick={() =>
                  setSelectedPickupLocations([
                    ...selectedPickupLocations,
                    getNewWishLocation(),
                  ])
                }
              />
            </div>
          )}
        </div>
      </Col>
    </Row>
  );
};

export default PickupLocationWaitingListSelector;
