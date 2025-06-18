import React, { useEffect, useState } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { Col, ListGroup, ListGroupItem, Row, Spinner } from "react-bootstrap";
import { PickupLocationsApi, PublicPickupLocation } from "../../api-client";
import formatAddress from "../../utils/formatAddress.ts";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import "../map.css";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapRef } from "react-leaflet/MapContainer";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { formatOpeningTimes } from "../utils/formatOpeningTimes.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { isShoppingCartEmpty } from "../utils/isShoppingCartEmpty.ts";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface BestellWizardPickupLocationProps {
  theme: TapirTheme;
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocation: PublicPickupLocation | undefined;
  setSelectedPickupLocation: (
    selectedPickupLocation: PublicPickupLocation,
  ) => void;
  shoppingCart: ShoppingCart;
  waitingListModeEnabled: boolean;
  csrfToken: string;
}

const BestellWizardPickupLocation: React.FC<
  BestellWizardPickupLocationProps
> = ({
  theme,
  pickupLocations,
  selectedPickupLocation,
  setSelectedPickupLocation,
  shoppingCart,
  waitingListModeEnabled,
  csrfToken,
}) => {
  const pickupLocationApi = useApi(PickupLocationsApi, csrfToken);
  const [
    pickupLocationsWithCapacityCheckLoading,
    setPickupLocationsWithCapacityCheckLoading,
  ] = useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [pickupLocationsWithCapacityFull, setPickupLocationsWithCapacityFull] =
    useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [map, setMap] = useState<MapRef>(null);

  useEffect(() => {
    if (selectedPickupLocation === undefined || map === null) return;

    map.setView(
      {
        lat: parseFloat(selectedPickupLocation.coordsLon),
        lng: parseFloat(selectedPickupLocation.coordsLat),
      },
      12,
      { animate: true },
    );
  }, [selectedPickupLocation]);

  useEffect(() => {
    if (pickupLocations.length === 0 || isShoppingCartEmpty(shoppingCart)) {
      return;
    }

    setPickupLocationsWithCapacityCheckLoading(new Set(pickupLocations));

    for (const pickupLocation of pickupLocations) {
      pickupLocationApi
        .pickupLocationsApiPickupLocationCapacityCheckCreate({
          pickupLocationCapacityCheckRequestRequest: {
            pickupLocationId: pickupLocation.id!,
            shoppingCart: shoppingCart,
          },
        })
        .then((response) => {
          setPickupLocationsWithCapacityFull((set) => {
            if (response.enoughCapacityForOrder) {
              set.delete(pickupLocation);
            } else {
              set.add(pickupLocation);
            }
            return new Set(set);
          });
        })
        .catch(handleRequestError)
        .finally(() => {
          setPickupLocationsWithCapacityCheckLoading((set) => {
            set.delete(pickupLocation);
            return new Set(set);
          });
        });
    }
  }, [pickupLocations, shoppingCart]);

  function buildCapacityIndicator(pickupLocation: PublicPickupLocation) {
    if (pickupLocationsWithCapacityCheckLoading.has(pickupLocation)) {
      return <Spinner size={"sm"} />;
    }

    if (pickupLocationsWithCapacityFull.has(pickupLocation)) {
      return <span className={"text-danger"}>Ausgelastet</span>;
    }

    return <span className={"text-success"}>Kapazität frei</span>;
  }

  return (
    <>
      <Row>
        <Col>
          <BestellWizardCardTitle text={"Deine Verteilstation"} />
          <BestellWizardCardSubtitle text={"Wähle deine Verteilstation"} />
          <p>
            Jede Woche wird dein Ernteanteil an eine Verteilstation deiner Wahl
            geliefert. Du kannst deine Station während der Vertragslaufzeit auch
            wechseln, z.B. wenn du umziehst oder Freunde deinen Anteil abholen.
          </p>
          <p>
            Ausgegraute Stationen sind derzeit komplett belegt. Du kannst dich
            auf die Warteliste setzen lassen. Erst wenn ein Mitglied hier
            kündigt, wird wieder ein Platz frei.{" "}
          </p>
        </Col>
      </Row>
      <Row>
        <Col>
          <ListGroup style={{ maxHeight: "50vh", overflow: "scroll" }}>
            {pickupLocations.map((pickupLocation) => (
              <ListGroupItem
                key={pickupLocation.id}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedPickupLocation(pickupLocation)}
                className={
                  selectedPickupLocation === pickupLocation ? "active" : ""
                }
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
                  <div
                    className={"d-flex flex-column gap-2 align-items-center"}
                  >
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
      <Row className={"mt-4"}>
        <BestellWizardCardSubtitle text={"Deine erste Lieferung"} />
        <p>
          Dein erster Ernteanteil kann an dieser Station am XX.XX.XXX geliefert
          werden.
        </p>
        <p>
          Alle weiteren Informationen zur Lieferung des ersten Ernteanteils
          werden an deine angegebene E-Mail-Adresse versandt. Bitte überprüfe
          ggf. deinen Spam-Ordner.
        </p>
        <p>
          Deine 6-wöchige Probezeit beginnt erst, nachdem du die erste Lieferung
          erhalten hast. Während der Probezeit besteht keine Kündigungsfrist und
          Du kannst Deinen Ernteanteil wöchentlich jeweils zum Freitag der
          Vorwoche kündigen. Du zahlst nur die Anteile, die du erhalten hast.
          Nach der Probezeit ist eine Kündigung nur zum Jahresende möglich.
        </p>
      </Row>
    </>
  );
};

export default BestellWizardPickupLocation;
