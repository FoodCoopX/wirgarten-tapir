import React, { useEffect, useState } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { Col, ListGroup, ListGroupItem, Row } from "react-bootstrap";
import {
  PickupLocationOpeningTime,
  PublicPickupLocation,
} from "../../api-client";
import formatAddress from "../../utils/formatAddress.ts";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import "../map.css";
import "leaflet/dist/leaflet.css";

import icon from "leaflet/dist/images/marker-icon.png";
import iconShadow from "leaflet/dist/images/marker-shadow.png";
import L from "leaflet";
import { MapRef } from "react-leaflet/MapContainer";

interface BestellWizardPickupLocationProps {
  theme: TapirTheme;
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocation: PublicPickupLocation | undefined;
  setSelectedPickupLocation: (
    selectedPickupLocation: PublicPickupLocation,
  ) => void;
}

const BestellWizardPickupLocation: React.FC<
  BestellWizardPickupLocationProps
> = ({
  theme,
  pickupLocations,
  selectedPickupLocation,
  setSelectedPickupLocation,
}) => {
  const [map, setMap] = useState<MapRef>(null);

  function compareOpeningTimes(
    a: PickupLocationOpeningTime,
    b: PickupLocationOpeningTime,
  ) {
    if (a.dayOfWeek !== b.dayOfWeek) {
      return a.dayOfWeek - b.dayOfWeek;
    }

    return (
      parseInt(a.openTime.split(":")[0]) - parseInt(b.openTime.split(":")[0])
    );
  }

  function buildOpeningTimes(pickupLocation: PublicPickupLocation) {
    return pickupLocation.openingTimes
      .sort(compareOpeningTimes)
      .map((openingTime) => {
        return (
          openingTime.dayOfWeekString.substring(0, 2) +
          " " +
          openingTime.openTime.substring(0, 5) +
          "-" +
          openingTime.closeTime.substring(0, 5)
        );
      })
      .join(", ");
  }

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

  return (
    <>
      <Row>
        <Col>
          <h1 className={"text-center"}>Deine Verteilstation</h1>
          <h3>Wähle deine Verteilstation</h3>
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
                <strong>{pickupLocation.name}</strong>
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
                <small>{buildOpeningTimes(pickupLocation)}</small>
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
                icon={L.icon({ iconUrl: icon, shadowUrl: iconShadow })}
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
                    <div>{buildOpeningTimes(pickupLocation)}</div>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </Col>
      </Row>
      <Row className={"mt-4"}>
        <h3>Deine erste Lieferung</h3>
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
