import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { PublicProductType } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { Col, Row } from "react-bootstrap";
import ProductForm from "../ProductForm.tsx";

interface BestellWizardProductTypeProps {
  theme: TapirTheme;
  productType: PublicProductType;
  shoppingCart: ShoppingCart;
  setShoppingCart: (shoppingCart: ShoppingCart) => void;
}

const BestellWizardProductType: React.FC<BestellWizardProductTypeProps> = ({
  theme,
  productType,
  shoppingCart,
  setShoppingCart,
}) => {
  function getHtmlDescription(description: string) {
    return { __html: description };
  }

  return (
    <>
      <Row>
        <Col>
          <h1 className={"text-center"}>{productType.name}</h1>
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
          />
        </Col>
      </Row>
    </>
  );
};

export default BestellWizardProductType;
