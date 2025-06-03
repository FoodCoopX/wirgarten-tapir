import React from "react";
import { Col, Row } from "react-bootstrap";
import { PublicProductType } from "../../api-client";
import { BESTELL_WIZARD_COLUMN_SIZE } from "../BESTELL_WIZARD_COLUMN_SIZE.ts";
import TapirButton from "../../components/TapirButton.tsx";
import ProductForm from "../ProductForm.tsx";

interface BestellWizardProductTypeBiotopProps {
  productType: PublicProductType;
  onProductTypeNextClicked: () => void;
  onProductTypePreviousClicked: () => void;
}

const BestellWizardProductTypeBiotop: React.FC<
  BestellWizardProductTypeBiotopProps
> = ({
  productType,
  onProductTypeNextClicked,
  onProductTypePreviousClicked,
}) => {
  function getHtmlDescription(description: string) {
    return { __html: description };
  }

  return (
    <>
      <Row className={"justify-content-center"}>
        <Col sm={BESTELL_WIZARD_COLUMN_SIZE}>
          <h1>{productType.name}</h1>
          {
            <span
              dangerouslySetInnerHTML={getHtmlDescription(
                productType.descriptionBestellwizardLong!,
              )}
            ></span>
          }
        </Col>
      </Row>
      <Row className={"justify-content-center"}>
        <Col sm={BESTELL_WIZARD_COLUMN_SIZE}>
          <ProductForm productType={productType} />
        </Col>
      </Row>
      <Row className={"justify-content-center mt-4 mb-2"}>
        <Col sm={BESTELL_WIZARD_COLUMN_SIZE}>
          <Row className={"justify-content-between"}>
            <Col>
              <TapirButton
                icon={"arrow_backward"}
                variant={"outline-primary"}
                text={"Zurück"}
                onClick={onProductTypePreviousClicked}
              />
            </Col>
            <Col className={"d-flex justify-content-end"}>
              <TapirButton
                icon={"arrow_forward"}
                variant={"outline-primary"}
                text={"Weiter"}
                onClick={onProductTypeNextClicked}
              />
            </Col>
          </Row>
        </Col>
      </Row>
    </>
  );
};

export default BestellWizardProductTypeBiotop;
