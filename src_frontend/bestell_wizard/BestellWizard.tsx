import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./BestellWizardIntro.tsx";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Col, Row, Spinner } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { useApi } from "../hooks/useApi.ts";
import {
  CoreApi,
  type PublicProductType,
  SubscriptionsApi,
} from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BestellWizardProductType from "./BestellWizardProductType.tsx";
import { sortProductTypes } from "./sortProductTypes.ts";
import { ShoppingCart } from "./ShoppingCart.ts";

interface BestellWizardProps {
  csrfToken: string;
}

type BestellWizardStep = "intro" | "products";

const BestellWizard: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  const [theme, setTheme] = useState<TapirTheme>();
  const coreApi = useApi(CoreApi, csrfToken);
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const [selectedProductTypes, setSelectedProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [currentStep, setCurrentStep] = useState<BestellWizardStep>("intro");
  const [currentProductType, setCurrentProductType] =
    useState<PublicProductType>();
  const [publicProductTypes, setPublicProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});

  useEffect(() => {
    coreApi
      .coreApiGetThemeRetrieve()
      .then((themeAsString) => {
        setTheme(themeAsString as TapirTheme);
      })
      .catch(handleRequestError);

    subscriptionsApi
      .subscriptionsPublicProductTypesList()
      .then((types) => {
        setPublicProductTypes(sortProductTypes(types));
      })
      .catch(handleRequestError);
  }, []);

  useEffect(() => {
    const newShoppingCart: ShoppingCart = {};
    for (const productType of publicProductTypes) {
      for (const product of productType.products) {
        newShoppingCart[product.id!] = 0;
      }
    }
    setShoppingCart(newShoppingCart);
  }, [publicProductTypes]);

  function onIntroNextClicked() {
    if (currentStep !== "intro") return;
    setCurrentStep("products");
    setCurrentProductType(selectedProductTypes[0]);
  }

  function onProductTypeNextClicked() {
    if (currentProductType === undefined) return;

    const indexOfCurrentProductType =
      selectedProductTypes.indexOf(currentProductType);

    if (indexOfCurrentProductType === selectedProductTypes.length - 1) {
      alert("Last product reached, WIP");
      return;
    }

    setCurrentProductType(selectedProductTypes[indexOfCurrentProductType + 1]);
  }

  function onProductTypePreviousClicked() {
    if (currentProductType === undefined) return;

    const indexOfCurrentProductType =
      selectedProductTypes.indexOf(currentProductType);

    if (indexOfCurrentProductType === 0) {
      setCurrentStep("intro");
      return;
    }

    setCurrentProductType(selectedProductTypes[indexOfCurrentProductType - 1]);
  }

  if (theme === undefined) {
    return (
      <Row>
        <Col>
          <Spinner />
        </Col>
      </Row>
    );
  }

  return (
    <>
      {currentStep === "intro" && (
        <BestellWizardIntro
          theme={theme}
          selectedProductTypes={selectedProductTypes}
          setSelectedProductTypes={setSelectedProductTypes}
          onIntroNextClicked={onIntroNextClicked}
          publicProductTypes={publicProductTypes}
        />
      )}
      {currentStep === "products" && currentProductType && (
        <BestellWizardProductType
          theme={theme}
          productType={currentProductType}
          onProductTypeNextClicked={onProductTypeNextClicked}
          onProductTypePreviousClicked={onProductTypePreviousClicked}
          shoppingCart={shoppingCart}
          setShoppingCart={setShoppingCart}
        />
      )}
    </>
  );
};

export default BestellWizard;
