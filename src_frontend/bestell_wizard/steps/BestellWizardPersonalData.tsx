import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { Col, Form, Row } from "react-bootstrap";
import { PersonalData } from "../types/PersonalData.ts";
import dayjs from "dayjs";
import BestellWizardCardTitle from "../BestellWizardCardTitle.tsx";

interface BestellWizardPersonalDataProps {
  theme: TapirTheme;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
}

const BestellWizardPersonalData: React.FC<BestellWizardPersonalDataProps> = ({
  theme,
  personalData,
  setPersonalData,
}) => {
  function updatePersonalData() {
    setPersonalData(Object.assign({}, personalData));
  }

  return (
    <>
      <Row>
        <Col className={""}>
          <BestellWizardCardTitle text={"Deine persönliche Daten"} />
        </Col>
      </Row>
      <Row>
        <Col>
          <Form.Group>
            <Form.Label>Vorname</Form.Label>
            <Form.Control
              value={personalData.firstName}
              onChange={(event) => {
                personalData.firstName = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Vorname"}
            />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Nachname</Form.Label>
            <Form.Control
              value={personalData.lastName}
              onChange={(event) => {
                personalData.lastName = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Nachname"}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row>
        <Col>
          <Form.Group>
            <Form.Label>E-Mail-Adresse</Form.Label>
            <Form.Control
              value={personalData.email}
              onChange={(event) => {
                personalData.email = event.target.value;
                updatePersonalData();
              }}
              type="email"
              placeholder={"E-Mail-Adresse"}
            />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Telefon-Nr</Form.Label>
            <Form.Control
              value={personalData.phoneNumber}
              onChange={(event) => {
                personalData.phoneNumber = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Telefon-Nr"}
              type={"tel"}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row>
        <Col>
          <Form.Group>
            <Form.Label>Straße & Hausnummer</Form.Label>
            <Form.Control
              value={personalData.street}
              onChange={(event) => {
                personalData.street = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Straße & Hausnummer"}
            />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Adresszusatz</Form.Label>
            <Form.Control
              value={personalData.street2}
              onChange={(event) => {
                personalData.street2 = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Adresszusatz"}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row>
        <Col>
          <Form.Group>
            <Form.Label>Postleitzahl</Form.Label>
            <Form.Control
              value={personalData.postCode}
              onChange={(event) => {
                personalData.postCode = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Postleitzahl"}
            />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Stadt</Form.Label>
            <Form.Control
              value={personalData.city}
              onChange={(event) => {
                personalData.city = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Stadt"}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row>
        <Col>
          <Form.Group>
            <Form.Label>Land</Form.Label>
            <Form.Control value={"Deutschland"} disabled={true} />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Geburtsdatum</Form.Label>
            <Form.Control
              onChange={(event) => {
                personalData.birthdate = new Date(event.target.value);
              }}
              value={dayjs(personalData.birthdate).format("YYYY-MM-DD")}
              placeholder={"Geburtsdatum"}
              type={"date"}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row>
        <Col>
          <Form.Label>Kontoinhaber*in</Form.Label>
          <Form.Control
            value={personalData.account_owner}
            onChange={(event) => {
              personalData.account_owner = event.target.value;
              updatePersonalData();
            }}
            placeholder={"Kontoinhaber*in"}
          />
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>IBAN</Form.Label>
            <Form.Control
              value={personalData.iban}
              onChange={(event) => {
                personalData.iban = event.target.value;
                updatePersonalData();
              }}
              placeholder={"IBAN"}
            />
          </Form.Group>
        </Col>
      </Row>
    </>
  );
};

export default BestellWizardPersonalData;
