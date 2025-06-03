import React from "react";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Col, ListGroup, ListGroupItem, Row } from "react-bootstrap";
import { PickupLocationOpeningTime, PublicPickupLocation } from "../api-client";
import formatAddress from "../utils/formatAddress.ts";

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

  return (
    <>
      <Row>
        <Col>
          <h1>Deine Verteilstation</h1>
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
          <ListGroup>
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
        <Col>Here goes the map</Col>
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
