import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./steps/BestellWizardIntro.tsx";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Card, Col, Row, Spinner } from "react-bootstrap";

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
import BestellWizardProductType from "./steps/BestellWizardProductType.tsx";
import { sortProductTypes } from "./utils/sortProductTypes.ts";
import { ShoppingCart } from "./types/ShoppingCart.ts";
import WaitingListModal from "./WaitingListModal.tsx";
import { WaitingListMode } from "./types/WaitingListMode.ts";
import BestellWizardPickupLocation from "./steps/BestellWizardPickupLocation.tsx";
import { BESTELL_WIZARD_COLUMN_SIZE } from "./utils/BESTELL_WIZARD_COLUMN_SIZE.ts";
import TapirButton from "../components/TapirButton.tsx";
import BestellWizardCoopShares from "./steps/BestellWizardCoopShares.tsx";
import BestellWizardPersonalData from "./steps/BestellWizardPersonalData.tsx";
import { PersonalData } from "./types/PersonalData.ts";
import { getEmptyPersonalData } from "./utils/getEmptyPersonalData.ts";

interface BestellWizardProps {
  csrfToken: string;
}

type BestellWizardStep =
  | "intro"
  | "products"
  | "pickup_location"
  | "coop_shares"
  | "personal_data";

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
  const [selectedNumberOfCoopShares, setSelectedNumberOfCoopShares] =
    useState(0);
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );

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
        setCurrentStep("coop_shares");
        return;
      case "coop_shares":
        setCurrentStep("personal_data");
        return;
      case "personal_data":
        alert("Not implemented yet!");
        return;
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
        return;
      case "coop_shares":
        setCurrentStep("pickup_location");
        return;
      case "personal_data":
        setCurrentStep("coop_shares");
        return;
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
      case "coop_shares":
        return (
          <BestellWizardCoopShares
            theme={theme}
            shoppingCart={shoppingCart}
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            setSelectedNumberOfCoopShares={setSelectedNumberOfCoopShares}
          />
        );
      case "personal_data":
        return (
          <BestellWizardPersonalData
            theme={theme}
            personalData={personalData}
            setPersonalData={setPersonalData}
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
        console.log(selectedPickupLocation);
        console.log(selectedPickupLocation !== undefined);
        return selectedPickupLocation !== undefined;
      case "coop_shares":
        return true;
      case "personal_data":
        return false;
    }
  }

  return (
    <>
      <Row className={"justify-content-center p-4"}>
        <Col sm={BESTELL_WIZARD_COLUMN_SIZE}>
          <Card style={{ height: "95vh" }}>
            <Card.Header>
              <h2 className={"text-center mb-0"}>Biotop Oberland eG</h2>
            </Card.Header>
            <Card.Body className={"overflow-scroll"}>
              {buildCurrentStepComponent()}
            </Card.Body>
            <Card.Footer>
              <div className={"d-flex justify-content-between"}>
                <TapirButton
                  icon={"arrow_backward"}
                  variant={"outline-primary"}
                  text={"Zurück"}
                  onClick={onBackClicked}
                  disabled={currentStep === "intro"}
                />
                <TapirButton
                  icon={"arrow_forward"}
                  variant={"outline-primary"}
                  text={"Weiter"}
                  onClick={onNextClicked}
                  disabled={!isNextEnabled()}
                />
              </div>
            </Card.Footer>
          </Card>

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
