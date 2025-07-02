import React from "react";
import { Col, Form, Modal, Row } from "react-bootstrap";
import ProductForm from "../../../bestell_wizard/components/ProductForm";
import { PublicProductType } from "../../../api-client";
import { ShoppingCart } from "../../../bestell_wizard/types/ShoppingCart.ts";
import { getTextSepaCheckbox } from "../../../bestell_wizard/utils/getTextSepaCheckbox.ts";
import TapirButton from "../../../components/TapirButton.tsx";

interface SubscriptionEditStepProductTypeProps {
  productType: PublicProductType;
  shoppingCart: ShoppingCart;
  setShoppingCart: (cart: ShoppingCart) => void;
  sepaAllowed: boolean;
  setSepaAllowed: (allowed: boolean) => void;
  onCancelClicked: () => void;
  loading: boolean;
  checkingCapacities: boolean;
  onNextClicked: () => void;
}

const SubscriptionEditStepProductType: React.FC<
  SubscriptionEditStepProductTypeProps
> = ({
  productType,
  shoppingCart,
  setShoppingCart,
  sepaAllowed,
  setSepaAllowed,
  onCancelClicked,
  loading,
  checkingCapacities,
  onNextClicked,
}) => {
  return (
    <>
      <Modal.Body style={{ maxHeight: "65vh", overflowY: "scroll" }}>
        <Row>
          <Col>
            <ProductForm
              productType={productType}
              shoppingCart={shoppingCart}
              setShoppingCart={setShoppingCart}
            />
          </Col>
        </Row>
        <Row>
          <Col>
            <Form.Check
              id={"sepa-mandat"}
              label={getTextSepaCheckbox()}
              checked={sepaAllowed}
              onChange={(event) => setSepaAllowed(event.target.checked)}
            />
          </Col>
        </Row>
      </Modal.Body>
      <Modal.Footer>
        <div
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
          style={{ width: "100%" }}
        >
          <TapirButton
            variant={"outline-secondary"}
            icon={"cancel"}
            iconPosition={"left"}
            text={"Abbrechen"}
            onClick={onCancelClicked}
          />
          <TapirButton
            variant={"outline-primary"}
            icon={"chevron_right"}
            text={
              sepaAllowed
                ? "Weiter"
                : "Ermächtige das SEPA-Mandat um weiter zu gehen"
            }
            iconPosition={"right"}
            disabled={!sepaAllowed}
            loading={loading || checkingCapacities}
            onClick={onNextClicked}
          />
        </div>
      </Modal.Footer>
    </>
  );
};

export default SubscriptionEditStepProductType;
