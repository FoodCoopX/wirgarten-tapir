import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { Col, Form, Row } from "react-bootstrap";
import { PersonalData } from "../types/PersonalData.ts";

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
        <Col>
          <Form.Group>
            <Form.Label>Vorname</Form.Label>
            <Form.Control
              value={personalData.firstName}
              onChange={(event) => {
                personalData.firstName = event.target.value;
                updatePersonalData();
              }}
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>Vorname</Form.Label>
            <Form.Control
              value={personalData.lastName}
              onChange={(event) => {
                personalData.lastName = event.target.value;
                updatePersonalData();
              }}
            />
          </Form.Group>
        </Col>
        <Col></Col>
      </Row>
    </>
  );
};

export default BestellWizardPersonalData;
