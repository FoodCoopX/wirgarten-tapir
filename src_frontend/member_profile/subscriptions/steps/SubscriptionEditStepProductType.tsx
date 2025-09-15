import React from "react";
import { Col, Form, Modal, Row } from "react-bootstrap";
import ProductForm from "../../../bestell_wizard/components/ProductForm";
import { PublicProductType } from "../../../api-client";
import { ShoppingCart } from "../../../bestell_wizard/types/ShoppingCart.ts";
import TapirButton from "../../../components/TapirButton.tsx";
import { isShoppingCartEmpty } from "../../../bestell_wizard/utils/isShoppingCartEmpty.ts";
import { BestellWizardSettings } from "../../../bestell_wizard/types/BestellWizardSettings.ts";

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
  settings: BestellWizardSettings;
  productIdsOverCapacity: string[];
  productTypeIdsOverCapacity: string[];
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
  settings,
  productIdsOverCapacity,
  productTypeIdsOverCapacity,
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
              waitingListLinkConfirmationModeEnabled={false}
              showHintFutureContract={true}
              settings={settings}
              productIdsOverCapacity={productIdsOverCapacity}
              productTypeIdsOverCapacity={productTypeIdsOverCapacity}
            />
          </Col>
        </Row>
        <Row>
          <Col>
            <Form.Check
              id={"sepa-mandat"}
              label={
                <span
                  dangerouslySetInnerHTML={{
                    __html: settings.labelCheckboxSepaMandat,
                  }}
                />
              }
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
            disabled={!sepaAllowed || isShoppingCartEmpty(shoppingCart)}
            loading={loading || checkingCapacities}
            onClick={onNextClicked}
          />
        </div>
      </Modal.Footer>
    </>
  );
};

export default SubscriptionEditStepProductType;
