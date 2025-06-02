import React from "react";
import { Col, Row } from "react-bootstrap";

interface BestellWizardIntroL2gProps {}

const BestellWizardIntroL2g: React.FC<BestellWizardIntroL2gProps> = () => {
  return (
    <Row>
      <Col>
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
