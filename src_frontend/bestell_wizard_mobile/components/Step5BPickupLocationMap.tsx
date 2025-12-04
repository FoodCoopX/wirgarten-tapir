import React, { useEffect, useState } from "react";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../../bestell_wizard/utils/formatOpeningTimes.ts";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { MapRef } from "react-leaflet/MapContainer";
import L from "leaflet";
import "./map.css";
import "leaflet/dist/leaflet.css";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { getFirstDelivery } from "../utils/getFirstDelivery.ts";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import { buildFilteredShoppingCart } from "../../bestell_wizard/utils/buildFilteredShoppingCart.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

interface Step5BPickupLocationMapProps {
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  tabIsActive: boolean;
  mapRef: MapRef;
  setMapRef: (mr: MapRef) => void;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  firstDeliveryDatesByPickupLocationAndProductType: {
    [key: string]: { [key: string]: Date };
  };
  shoppingCart: ShoppingCart;
  productTypesInWaitingList: Set<PublicProductType>;
}

const Step5BPickupLocationMap: React.FC<Step5BPickupLocationMapProps> = ({
  pickupLocations,
  selectedPickupLocations,
  setSelectedPickupLocations,
  tabIsActive,
  mapRef,
  setMapRef,
  pickupLocationsWithCapacityFull,
  firstDeliveryDatesByPickupLocationAndProductType,
  shoppingCart,
  productTypesInWaitingList,
}) => {
  const [firstRender, setFirstRender] = useState(true);

  useEffect(() => {
    if (!mapRef) {
      return;
    }

    if (!tabIsActive) {
      mapRef.closePopup();
    }

    if (selectedPickupLocations.length === 0) {
      return;
    }

    mapRef.setView(
      {
        lat: parseFloat(selectedPickupLocations[0].coordsLon),
        lng: parseFloat(selectedPickupLocations[0].coordsLat),
      },
      15,
      { animate: true },
    );
  }, [selectedPickupLocations]);

  useEffect(() => {
    if (tabIsActive && mapRef) {
      setTimeout(() => {
        mapRef.invalidateSize(true);
        setTimeout(() => {
          if (firstRender) {
            setMapBoundaries();
            setFirstRender(false);
          }
        }, 10);
      }, 10);
    }
  }, [tabIsActive, mapRef]);

  function setMapBoundaries() {
    if (!mapRef) {
      return;
    }

    const bounds = L.latLngBounds(
      pickupLocations.map((pickupLocation) => [
        parseFloat(pickupLocation.coordsLon),
        parseFloat(pickupLocation.coordsLat),
      ]),
    );
    mapRef.fitBounds(bounds);
  }

  function updateSelection(pickupLocation: PublicPickupLocation) {
    if (selectedPickupLocations.includes(pickupLocation)) {
      setSelectedPickupLocations(
        selectedPickupLocations.filter((pl) => pl !== pickupLocation),
      );
      if (mapRef) {
        setMapBoundaries();
        mapRef.closePopup();
      }
    } else {
      setSelectedPickupLocations([pickupLocation]);
    }
  }

  function getMarkerIcon(pickupLocation: PublicPickupLocation) {
    if (selectedPickupLocations.includes(pickupLocation)) {
      return "marker-icon-green.png";
    }

    if (pickupLocationsWithCapacityFull.has(pickupLocation)) {
      return "marker-icon-red.png";
    }

    return "marker-icon.png";
  }

  function getPopupButtonText(pickupLocation: PublicPickupLocation) {
    if (pickupLocationsWithCapacityFull.has(pickupLocation)) {
      return selectedPickupLocations.includes(pickupLocation)
        ? "Als Wunsch eingetragen"
        : "Als Wunsch eintragen";
    }

    return selectedPickupLocations.includes(pickupLocation)
      ? "Ausgewählt"
      : "Auswählen";
  }

  return (
    <>
      <MapContainer
        center={[
          parseFloat(pickupLocations[0].coordsLon),
          parseFloat(pickupLocations[0].coordsLat),
        ]}
        zoom={13}
        scrollWheelZoom={true}
        ref={setMapRef}
        style={{ position: "absolute", top: 0, bottom: 0, right: 0, left: 0 }}
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
              iconUrl: "/static/subscriptions/" + getMarkerIcon(pickupLocation),
              shadowUrl: "/static/subscriptions/marker-shadow.png",
              iconAnchor: [13, 35],
              popupAnchor: [0, -33],
            })}
            key={pickupLocation.id}
          >
            <Popup>
              <div
                className={
                  "d-flex flex-column gap-2 align-items-center text-center"
                }
              >
                <strong>{pickupLocation.name}</strong>
                {pickupLocationsWithCapacityFull.has(pickupLocation) ? (
                  <span className={"text-danger"}>Ausgelastet</span>
                ) : (
                  <span className={"text-success"}>
                    {isAtLeastOneProductOrdered(
                      buildFilteredShoppingCart(
                        shoppingCart,
                        false,
                        productTypesInWaitingList,
                      ),
                    )
                      ? getFirstDelivery(
                          pickupLocation.id!,
                          firstDeliveryDatesByPickupLocationAndProductType,
                        )
                      : "Kapazität frei"}
                  </span>
                )}
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
                  text={getPopupButtonText(pickupLocation)}
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
