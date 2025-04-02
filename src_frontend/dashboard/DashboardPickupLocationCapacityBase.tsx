import React, { useEffect, useState } from "react";
import { Card, Form } from "react-bootstrap";
import { PickupLocation, PickupLocationsApi } from "../api-client";
import { useApi } from "../hooks/useApi.ts";

interface GrowingPeriodBaseProps {}

const DashboardPickupLocationCapacityBase: React.FC<
  GrowingPeriodBaseProps
> = ({}) => {
  const api = useApi(PickupLocationsApi, "no_token");
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [baseLoading, setBaseLoading] = useState(true);
  const [selectedPickupLocation, setSelectedPickupLocation] =
    useState<PickupLocation>();

  useEffect(() => {
    setBaseLoading(true);
    api
      .pickupLocationsPickupLocationsList()
      .then(setPickupLocations)
      .catch(alert)
      .finally(() => setBaseLoading(false));
  }, []);

  function onPickupLocationChanged(newLocationId: string) {
    for (const pickupLocation of pickupLocations) {
      if (pickupLocation.id === newLocationId) {
        setSelectedPickupLocation(pickupLocation);
        return;
      }
    }
    alert("Unknown pickup location with ID: " + newLocationId);
  }

  function pickupLocationSelect() {
    return (
      <Form.Select
        value={selectedPickupLocation?.id}
        onChange={(event) => onPickupLocationChanged(event.target.value)}
      >
        {pickupLocations.map((pickupLocation) => (
          <option key={pickupLocation.id} value={pickupLocation.id}>
            {pickupLocation.name}
          </option>
        ))}
      </Form.Select>
    );
  }

  return (
    <Card>
      <Card.Header>
        <div
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
        >
          <h5 className={"mb-0"}>Freiwerdende Kapazitäten</h5>
          {!baseLoading && pickupLocationSelect()}
        </div>
      </Card.Header>
      <Card.Body>
        {selectedPickupLocation && <>{selectedPickupLocation.name}</>}
      </Card.Body>
    </Card>
  );
};

export default DashboardPickupLocationCapacityBase;
