import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { Col, Row } from "react-bootstrap";
import ProductForm from "../components/ProductForm.tsx";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";

interface BestellWizardProductTypeProps {
  theme: TapirTheme;
  productType: PublicProductType;
  shoppingCart: ShoppingCart;
  setShoppingCart: (shoppingCart: ShoppingCart) => void;
  waitingListLinkConfirmationModeEnabled: boolean;
}

const BestellWizardProductType: React.FC<BestellWizardProductTypeProps> = ({
  theme,
  productType,
  shoppingCart,
  setShoppingCart,
  waitingListLinkConfirmationModeEnabled,
}) => {
  function getHtmlDescription(description: string) {
    return { __html: description };
  }

  return (
    <>
      <Row>
        <Col>
          <BestellWizardCardTitle text={productType.name} />
          {
            <span
              dangerouslySetInnerHTML={getHtmlDescription(
                productType.descriptionBestellwizardLong!,
              )}
            ></span>
          }
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
          />
        </Col>
      </Row>
    </>
  );
};

export default BestellWizardProductType;
