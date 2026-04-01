import React from "react";
import { PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { Col, Row } from "react-bootstrap";
import ProductForm from "../components/ProductForm.tsx";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";

interface BestellWizardProductTypeProps {
  productType: PublicProductType;
  shoppingCart: ShoppingCart;
  setShoppingCart: (shoppingCart: ShoppingCart) => void;
  waitingListLinkConfirmationModeEnabled: boolean;
  settings: BestellWizardSettings;
  productIdsOverCapacity: string[];
  productTypeIdsOverCapacity: string[];
}

const BestellWizardProductType: React.FC<BestellWizardProductTypeProps> = ({
  productType,
  shoppingCart,
  setShoppingCart,
  waitingListLinkConfirmationModeEnabled,
  settings,
  productIdsOverCapacity,
  productTypeIdsOverCapacity,
}) => {
  function getHtmlDescription(description: string) {
    return { __html: description };
  }

  return (
    <>
      <Row>
        <Col>
          <BestellWizardCardTitle text={productType.name} />
          <span
            dangerouslySetInnerHTML={getHtmlDescription(
              productType.descriptionBestellwizardLong!,
            )}
          />
        </Col>
      </Row>
      <Row>
        <Col>
          <ProductForm
            productType={productType}
            shoppingCart={shoppingCart}
            setShoppingCart={setShoppingCart}
            waitingListLinkConfirmationModeEnabled={
              waitingListLinkConfirmationModeEnabled
            }
            showHintFutureContract={false}
            settings={settings}
            productIdsOverCapacity={productIdsOverCapacity}
            productTypeIdsOverCapacity={productTypeIdsOverCapacity}
          />
        </Col>
      </Row>
    </>
  );
};

export default BestellWizardProductType;
