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
import BestellWizardPickupLocation from "./steps/BestellWizardPickupLocation.tsx";
import TapirButton from "../components/TapirButton.tsx";
import BestellWizardCoopShares from "./steps/BestellWizardCoopShares.tsx";
import BestellWizardPersonalData from "./steps/BestellWizardPersonalData.tsx";
import { PersonalData } from "./types/PersonalData.ts";
import { getEmptyPersonalData } from "./utils/getEmptyPersonalData.ts";
import BestellWizardSummary from "./steps/BestellWizardSummary.tsx";
import { isProductTypeOrdered } from "./utils/isProductTypeOrdered.ts";
import { isPersonalDataValid } from "./utils/isPersonalDataValid.ts";

interface BestellWizardProps {
  csrfToken: string;
}

type BestellWizardStep =
  | "intro"
  | "pickup_location"
  | "coop_shares"
  | "personal_data"
  | "summary";

const BestellWizard: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  const [theme, setTheme] = useState<TapirTheme>();
  const coreApi = useApi(CoreApi, csrfToken);
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const pickupLocationApi = useApi(PickupLocationsApi, csrfToken);
  const [selectedProductTypes, setSelectedProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [currentStep, setCurrentStep] = useState<BestellWizardStep | string>(
    "intro",
  );
  const [publicProductTypes, setPublicProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
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
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [contractRead, setContractRead] = useState(false);
  const [steps, setSteps] = useState<(string | BestellWizardStep)[]>(["intro"]);
  const [statuteRead, setStatuteRead] = useState(false);

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

  useEffect(() => {
    setSteps([
      "intro",
      ...selectedProductTypes.map((productType) => productType.id!),
      "pickup_location",
      "coop_shares",
      "personal_data",
      "summary",
    ]);
  }, [selectedProductTypes]);

  function onNextClicked() {
    setCurrentStep(steps[steps.indexOf(currentStep) + 1]);
  }

  function onBackClicked() {
    setCurrentStep(steps[steps.indexOf(currentStep) - 1]);
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
            statuteRead={statuteRead}
            setStatuteRead={setStatuteRead}
          />
        );
      case "personal_data":
        return (
          <BestellWizardPersonalData
            theme={theme}
            personalData={personalData}
            setPersonalData={setPersonalData}
            sepaAllowed={sepaAllowed}
            setSepaAllowed={setSepaAllowed}
            contractRead={contractRead}
            setContractRead={setContractRead}
          />
        );
      case "summary":
        return (
          <BestellWizardSummary
            theme={theme}
            shoppingCart={shoppingCart}
            personalData={personalData}
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            productTypes={publicProductTypes}
            pickupLocation={selectedPickupLocation}
          />
        );
      default:
        const productType = publicProductTypes.find(
          (productType) => productType.id === currentStep,
        );
        if (productType === undefined) {
          return <div>Product type with id {currentStep} not found</div>;
        }
        return (
          <BestellWizardProductType
            theme={theme}
            productType={productType}
            shoppingCart={shoppingCart}
            setShoppingCart={setShoppingCart}
          />
        );
    }
  }

  function isNextEnabled() {
    switch (currentStep) {
      case "intro":
        return selectedProductTypes.length > 0;
      case "pickup_location":
        return selectedPickupLocation !== undefined;
      case "coop_shares":
        return statuteRead;
      case "personal_data":
        return isPersonalDataValid(personalData) && sepaAllowed && contractRead;
      case "summary":
        return false;
      default:
        return true;
    }
  }

  function getNextButton() {
    if (currentStep === "summary") {
      return (
        <TapirButton
          icon={"check"}
          variant={"primary"}
          text={"Bestellung abschließen"}
          onClick={() => alert("TODO : actually order")}
          iconPosition={"right"}
        />
      );
    }

    const productType = publicProductTypes.find(
      (productType) => productType.id === currentStep,
    );
    if (productType !== undefined) {
      if (isProductTypeOrdered(productType, shoppingCart)) {
        return (
          <TapirButton
            icon={"add_shopping_cart"}
            variant={"outline-primary"}
            text={productType.name + " zur Bestellung hinzufügen"}
            onClick={onNextClicked}
            iconPosition={"right"}
          />
        );
      }
      return (
        <TapirButton
          icon={"shopping_cart_off"}
          variant={"outline-primary"}
          text={"Ohne " + productType.name + " weitergehen"}
          onClick={onNextClicked}
          iconPosition={"right"}
        />
      );
    }

    let text = "Weiter";

    switch (currentStep) {
      case "intro":
        if (selectedProductTypes.length === 0) {
          text = "Wähle mindestens eine Mitgliedschaft um weiter zu gehen";
        }
        break;
      case "pickup_location":
        if (selectedPickupLocation === undefined) {
          text = "Wähle dein Verteilstation aus um weiter zu gehen";
        }
        break;
      case "coop_shares":
        if (!statuteRead) {
          text = "Akzeptiere die Satzung um weiter zu gehen";
        }
        break;
      case "personal_data":
        if (!isPersonalDataValid(personalData)) {
          text = "Vervollständige deine Daten um weiter zu gehen";
        } else if (!sepaAllowed) {
          text = "Ermächtige das SEPA-Mandat um weiter zu gehen";
        } else if (!contractRead) {
          text = "Akzeptiere die Vertragsgrundsätze um weiter zu gehen";
        }
    }
    return (
      <TapirButton
        icon={"chevron_right"}
        variant={"outline-primary"}
        text={text}
        onClick={onNextClicked}
        disabled={!isNextEnabled()}
        iconPosition={"right"}
      />
    );
  }

  return (
    <>
      <Row className={"justify-content-center p-4"}>
        <Col style={{ maxWidth: "1200px" }}>
          <Card style={{ height: "95vh" }}>
            <Card.Header>
              <h2 className={"text-center mb-0"}>Biotop Oberland eG</h2>
            </Card.Header>
            <Card.Body className={"overflow-scroll"}>
              {buildCurrentStepComponent()}
            </Card.Body>
            <Card.Footer>
              <div className={"d-flex justify-content-between"}>
                <div className={"d-flex flex-row gap-2"}>
                  <TapirButton
                    icon={"first_page"}
                    variant={"outline-primary"}
                    onClick={() => {
                      setCurrentStep("intro");
                    }}
                    disabled={currentStep === "intro"}
                  />
                  <TapirButton
                    icon={"chevron_left"}
                    variant={"outline-primary"}
                    text={"Zurück"}
                    onClick={onBackClicked}
                    disabled={currentStep === "intro"}
                  />
                </div>
                {getNextButton()}
              </div>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default BestellWizard;
