import React from "react";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Col, Row } from "react-bootstrap";

interface BestellWizardPickupLocationProps {
  theme: TapirTheme;
}

const BestellWizardPickupLocation: React.FC<
  BestellWizardPickupLocationProps
> = ({ theme }) => {
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
        <Col>Here goes the widget</Col>
      </Row>
      <Row>
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
