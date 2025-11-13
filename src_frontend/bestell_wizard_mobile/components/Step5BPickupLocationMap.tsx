import React, { useEffect, useState } from "react";
import { PublicPickupLocation } from "../../api-client";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../../bestell_wizard/utils/formatOpeningTimes.ts";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { MapRef } from "react-leaflet/MapContainer";
import L from "leaflet";
import "./map.css";
import "leaflet/dist/leaflet.css";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";

interface Step5BPickupLocationMapProps {
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  tabIsActive: boolean;
}

const Step5BPickupLocationMap: React.FC<Step5BPickupLocationMapProps> = ({
  pickupLocations,
  selectedPickupLocations,
  setSelectedPickupLocations,
  tabIsActive,
}) => {
  const [map, setMap] = useState<MapRef>(null);
  const [firstRender, setFirstRender] = useState(true);

  useEffect(() => {
    if (map === null) {
      return;
    }

    if (!tabIsActive) {
      map.closePopup();
    }

    if (selectedPickupLocations.length === 0) {
      return;
    }

    map.setView(
      {
        lat: parseFloat(selectedPickupLocations[0].coordsLon),
        lng: parseFloat(selectedPickupLocations[0].coordsLat),
      },
      15,
      { animate: true },
    );
  }, [selectedPickupLocations]);

  useEffect(() => {
    if (tabIsActive && map) {
      setTimeout(() => {
        map.invalidateSize(true);
        setTimeout(() => {
          if (firstRender) {
            setMapBoundaries();
            setFirstRender(false);
          }
        }, 10);
      }, 10);
    }
  }, [tabIsActive, map]);

  function setMapBoundaries() {
    if (!map) {
      return;
    }

    const bounds = L.latLngBounds(
      pickupLocations.map((pickupLocation) => [
        parseFloat(pickupLocation.coordsLon),
        parseFloat(pickupLocation.coordsLat),
      ]),
    );
    map.fitBounds(bounds);
  }

  function updateSelection(pickupLocation: PublicPickupLocation) {
    if (selectedPickupLocations.includes(pickupLocation)) {
      setSelectedPickupLocations(
        selectedPickupLocations.filter((pl) => pl !== pickupLocation),
      );
      if (map) {
        setMapBoundaries();
        map.closePopup();
      }
    } else {
      setSelectedPickupLocations([pickupLocation]);
    }
  }

  return (
    <>
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
              iconAnchor: [13, 35],
              popupAnchor: [0, -33],
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
                <TapirButton
                  size={"sm"}
                  text={
                    selectedPickupLocations.includes(pickupLocation)
                      ? "Ausgewählt"
                      : "Auswählen"
                  }
                  icon={
                    selectedPickupLocations.includes(pickupLocation)
                      ? "select_check_box"
                      : "check_box_outline_blank"
                  }
                  variant={
                    selectedPickupLocations.includes(pickupLocation)
                      ? "outline-success"
                      : BUTTON_VARIANT
                  }
                  onClick={() => updateSelection(pickupLocation)}
                />
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </>
  );
};

export default Step5BPickupLocationMap;
