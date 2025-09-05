import React, { useEffect, useState } from "react";
import { Col, ListGroup, ListGroupItem, Row, Spinner } from "react-bootstrap";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../utils/formatOpeningTimes.ts";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import "../map.css";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { PublicPickupLocation } from "../../api-client";
import { MapRef } from "react-leaflet/MapContainer";

interface PickupLocationSelectorProps {
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  waitingListModeEnabled: boolean;
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  waitingListLinkConfirmationModeEnabled: boolean;
}

const PickupLocationSelector: React.FC<PickupLocationSelectorProps> = ({
  pickupLocations,
  selectedPickupLocations,
  setSelectedPickupLocations,
  waitingListModeEnabled,
  pickupLocationsWithCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  waitingListLinkConfirmationModeEnabled,
}) => {
  const [map, setMap] = useState<MapRef>(null);

  useEffect(() => {
    if (selectedPickupLocations.length === 0 || map === null) {
      return;
    }

    map.setView(
      {
        lat: parseFloat(selectedPickupLocations[0].coordsLon),
        lng: parseFloat(selectedPickupLocations[0].coordsLat),
      },
      12,
      { animate: true },
    );
  }, [selectedPickupLocations]);

  function getClassForPickupLocationListItem(
    pickupLocation: PublicPickupLocation,
  ) {
    let result = "";
    if (selectedPickupLocations.includes(pickupLocation)) {
      result += "active";
    }

    if (!areListGroupItemsClickable()) {
      result += " disabled";
    }

    return result;
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

    return <span className={"text-success"}>Kapazität frei</span>;
  }

  function areListGroupItemsClickable() {
    if (waitingListLinkConfirmationModeEnabled) {
      return false;
    }

    if (!waitingListModeEnabled) {
      return true;
    }

    return selectedPickupLocations.length === 0;
  }

  return (
    <Row>
      <Col>
        <ListGroup style={{ maxHeight: "50vh", overflow: "scroll" }}>
          {pickupLocations.map((pickupLocation) => (
            <ListGroupItem
              key={pickupLocation.id}
              style={areListGroupItemsClickable() ? { cursor: "pointer" } : {}}
              onClick={() => {
                if (!areListGroupItemsClickable()) return;
                setSelectedPickupLocations([pickupLocation]);
              }}
              className={getClassForPickupLocationListItem(pickupLocation)}
            >
              <strong>{pickupLocation.name}</strong>{" "}
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
            </ListGroupItem>
          ))}
        </ListGroup>
      </Col>
      <Col>
        <MapContainer
          center={[
            parseFloat(pickupLocations[0].coordsLon),
            parseFloat(pickupLocations[0].coordsLat),
          ]}
          zoom={13}
          scrollWheelZoom={false}
          ref={setMap}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {pickupLocations.map((pickupLocation) => (
            <Marker
              position={[
                parseFloat(pickupLocation.coordsLon),
                parseFloat(pickupLocation.coordsLat),
              ]}
              icon={L.icon({
                iconUrl: "/static/subscriptions/marker-icon.png",
                shadowUrl: "/static/subscriptions/marker-shadow.png",
              })}
              key={pickupLocation.id}
            >
              <Popup>
                <div className={"d-flex flex-column gap-2 align-items-center"}>
                  <strong>{pickupLocation.name}</strong>
                  <div>
                    {formatAddress(
                      pickupLocation.street,
                      pickupLocation.street2,
                      pickupLocation.postcode,
                      pickupLocation.city,
                    )}
                  </div>
                  <div>{formatOpeningTimes(pickupLocation)}</div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </Col>
    </Row>
  );
};

export default PickupLocationSelector;
