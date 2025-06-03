import React from "react";
import { Col, Row } from "react-bootstrap";
import { BESTELL_WIZARD_COLUMN_SIZE } from "../BESTELL_WIZARD_COLUMN_SIZE.ts";

interface BestellWizardIntroL2gProps {}

const BestellWizardIntroL2g: React.FC<BestellWizardIntroL2gProps> = () => {
  return (
    <Row>
      <Col sm={BESTELL_WIZARD_COLUMN_SIZE}>
        <h1>Mitmachen im L2G</h1>
        <p>
          Du möchtest Teil des L2Gs werden? Dann gibt es jetzt verschiedene
          Möglichkeiten:
        </p>
      </Col>
    </Row>
  );
};

export default BestellWizardIntroL2g;
