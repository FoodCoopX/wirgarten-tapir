import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./BestellWizardIntro.tsx";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Col, Row, Spinner } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { useApi } from "../hooks/useApi.ts";
import {
  CoreApi,
  PickupLocationsApi,
  PublicPickupLocation,
  type PublicProductType,
  SubscriptionsApi,
} from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BestellWizardProductType from "./BestellWizardProductType.tsx";
import { sortProductTypes } from "./sortProductTypes.ts";
import { ShoppingCart } from "./ShoppingCart.ts";
import WaitingListModal from "./WaitingListModal.tsx";
import { WaitingListMode } from "./WaitingListMode.ts";
import BestellWizardPickupLocation from "./BestellWizardPickupLocation.tsx";
import { BESTELL_WIZARD_COLUMN_SIZE } from "./BESTELL_WIZARD_COLUMN_SIZE.ts";
import TapirButton from "../components/TapirButton.tsx";

interface BestellWizardProps {
  csrfToken: string;
}

type BestellWizardStep = "intro" | "products" | "pickup_location";

const BestellWizard: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  const [theme, setTheme] = useState<TapirTheme>();
  const coreApi = useApi(CoreApi, csrfToken);
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const pickupLocationApi = useApi(PickupLocationsApi, csrfToken);
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
  const [waitingListActivated, setWaitingListActivated] = useState(false);
  const [waitingListMode, setWaitingListMode] =
    useState<WaitingListMode>("general");
  const [showWaitingListModal, setShowWaitingListModal] = useState(false);
  const [pickupLocations, setPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [selectedPickupLocation, setSelectedPickupLocation] =
    useState<PublicPickupLocation>();

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

    pickupLocationApi
      .pickupLocationsPublicPickupLocationsList()
      .then(setPickupLocations)
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

  function onNextClicked() {
    switch (currentStep) {
      case "intro":
        setCurrentStep("products");
        setCurrentProductType(selectedProductTypes[0]);
        return;
      case "products":
        if (currentProductType === undefined) return;
        const indexOfCurrentProductType =
          selectedProductTypes.indexOf(currentProductType);

        if (indexOfCurrentProductType === selectedProductTypes.length - 1) {
          setCurrentStep("pickup_location");
          return;
        }

        setCurrentProductType(
          selectedProductTypes[indexOfCurrentProductType + 1],
        );
        return;
      case "pickup_location":
        alert("Not implemented yet!");
    }
  }

  function onBackClicked() {
    switch (currentStep) {
      case "intro":
        return;
      case "products":
        if (currentProductType === undefined) return;

        const indexOfCurrentProductType =
          selectedProductTypes.indexOf(currentProductType);

        if (indexOfCurrentProductType === 0) {
          setCurrentStep("intro");
          return;
        }

        setCurrentProductType(
          selectedProductTypes[indexOfCurrentProductType - 1],
        );
        return;
      case "pickup_location":
        setCurrentStep("products");
    }
  }

  function buildCurrentStepComponent() {
    if (theme === undefined) {
      return (
        <Row>
          <Col>
            <Spinner />
          </Col>
        </Row>
      );
    }

    switch (currentStep) {
      case "intro":
        return (
          <BestellWizardIntro
            theme={theme}
            selectedProductTypes={selectedProductTypes}
            setSelectedProductTypes={setSelectedProductTypes}
            publicProductTypes={publicProductTypes}
          />
        );
      case "products":
        if (currentProductType === undefined) {
          return <span>No current product type, this should not happen</span>;
        }
        return (
          <BestellWizardProductType
            theme={theme}
            productType={currentProductType}
            shoppingCart={shoppingCart}
            setShoppingCart={setShoppingCart}
          />
        );
      case "pickup_location":
        return (
          <BestellWizardPickupLocation
            theme={theme}
            pickupLocations={pickupLocations}
            selectedPickupLocation={selectedPickupLocation}
            setSelectedPickupLocation={setSelectedPickupLocation}
          />
        );
    }
  }

  function isNextEnabled() {
    switch (currentStep) {
      case "intro":
        return selectedProductTypes.length > 0;
      case "products":
        return true;
      case "pickup_location":
        return false;
    }
  }

  return (
    <>
      <Row className={"justify-content-center"}>
        <Col sm={BESTELL_WIZARD_COLUMN_SIZE}>
          {buildCurrentStepComponent()}
          <Row className={"justify-content-center mt-4 mb-2"}>
            <Col sm={BESTELL_WIZARD_COLUMN_SIZE}>
              <Row className={"justify-content-between"}>
                <Col>
                  <TapirButton
                    icon={"arrow_backward"}
                    variant={"outline-primary"}
                    text={"Zurück"}
                    onClick={onBackClicked}
                    disabled={currentStep === "intro"}
                  />
                </Col>
                <Col className={"d-flex justify-content-end"}>
                  <TapirButton
                    icon={"arrow_forward"}
                    variant={"outline-primary"}
                    text={"Weiter"}
                    onClick={onNextClicked}
                    disabled={!isNextEnabled()}
                  />
                </Col>
              </Row>
            </Col>
          </Row>
          <WaitingListModal
            show={showWaitingListModal}
            onHide={() => setShowWaitingListModal(false)}
            mode={waitingListMode}
          />
        </Col>
      </Row>
    </>
  );
};

export default BestellWizard;
