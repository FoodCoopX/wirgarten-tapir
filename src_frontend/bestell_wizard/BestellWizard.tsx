import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./steps/BestellWizardIntro.tsx";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Card, Col, Row, Spinner } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { useApi } from "../hooks/useApi.ts";
import {
  BestellWizardConfirmOrderResponse,
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
import { getTestPersonalData } from "./utils/getTestPersonalData.ts";
import BestellWizardEnd from "./steps/BestellWizardEnd.tsx";
import { buildNextButtonParametersForProductType } from "./utils/buildNextButtonForProductType.ts";
import BestellWizardNextButton from "./components/BestellWizardNextButton.tsx";
import ProductWaitingListModal from "./components/ProductWaitingListModal.tsx";

interface BestellWizardProps {
  csrfToken: string;
}

type BestellWizardStep =
  | "intro"
  | "pickup_location"
  | "coop_shares"
  | "personal_data"
  | "summary"
  | "end";

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
  const [contractAccepted, setContractAccepted] = useState(false);
  const [steps, setSteps] = useState<(string | BestellWizardStep)[]>(["intro"]);
  const [statuteAccepted, setStatuteAccepted] = useState(false);
  const [confirmOrderLoading, setConfirmOrderLoading] = useState(false);
  const [confirmOrderResponse, setConfirmOrderResponse] =
    useState<BestellWizardConfirmOrderResponse>();
  const [checkingCapacities, setCheckingCapacities] = useState(false);
  const [productIdsOverCapacity, setProductIdsOverCapacity] = useState<
    string[]
  >([]);
  const [productTypeIdsOverCapacity, setProductTypeIdsOverCapacity] = useState<
    string[]
  >([]);
  const [waitingListModeEnabled, setWaitingListModeEnabled] = useState(false);
  const [productWaitingListModalOpen, setProductWaitingListModalOpen] =
    useState(false);

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

    setSelectedProductTypes(
      publicProductTypes.filter(
        (productType) => productType.mustBeSubscribedTo,
      ),
    );
  }, [publicProductTypes]);

  useEffect(() => {
    setSteps([
      "intro",
      ...selectedProductTypes.map((productType) => productType.id!),
      "pickup_location",
      "coop_shares",
      "personal_data",
      "summary",
      "end",
    ]);
  }, [selectedProductTypes]);

  useEffect(() => {
    const totalQuantityOrdered = Object.values(shoppingCart).reduce(
      (sum, quantity) => sum + quantity,
      0,
    );
    if (totalQuantityOrdered === 0) {
      return;
    }

    setCheckingCapacities(true);

    subscriptionsApi
      .subscriptionsApiBestellWizardCapacityCheckCreate({
        bestellWizardCapacityCheckRequestRequest: {
          shoppingCart: shoppingCart,
        },
      })
      .then((response) => {
        setProductIdsOverCapacity(response.idsOfProductsOverCapacity);
        setProductTypeIdsOverCapacity(response.idsOfProductTypesOverCapacity);
        if (
          response.idsOfProductsOverCapacity.length === 0 &&
          response.idsOfProductTypesOverCapacity.length === 0
        ) {
          setWaitingListModeEnabled(false);
        }
      })
      .catch(handleRequestError)
      .finally(() => setCheckingCapacities(false));
  }, [shoppingCart]);

  function onNextClicked() {
    if (!waitingListModeEnabled && shouldOpenWaitingListModal()) {
      setProductWaitingListModalOpen(true);
      return;
    }
    goToNextStep();
  }

  function shouldOpenWaitingListModal() {
    const productType = publicProductTypes.find(
      (productType) => productType.id === currentStep,
    );
    if (productType === undefined) {
      return false;
    }

    if (productTypeIdsOverCapacity.includes(productType.id!)) {
      return true;
    }
    for (const product of productType.products) {
      if (productIdsOverCapacity.includes(product.id!)) {
        return true;
      }
    }

    return false;
  }

  function goToNextStep() {
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
            statuteAccepted={statuteAccepted}
            setStatuteAccepted={setStatuteAccepted}
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
            contractAccepted={contractAccepted}
            setContractAccepted={setContractAccepted}
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
      case "end":
        return (
          <BestellWizardEnd theme={theme} response={confirmOrderResponse!} />
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
        return statuteAccepted;
      case "personal_data":
        return (
          isPersonalDataValid(personalData) && sepaAllowed && contractAccepted
        );
      default:
        const productType = publicProductTypes.find(
          (productType) => productType.id === currentStep,
        );
        if (productType === undefined) return true;
        return (
          !productType.mustBeSubscribedTo ||
          !isProductTypeOrdered(productType, shoppingCart)
        );
    }
  }

  function onConfirmOrder() {
    setConfirmOrderLoading(true);

    subscriptionsApi
      .subscriptionsBestellWizardConfirmOrderCreate({
        bestellWizardConfirmOrderRequestRequest: {
          personalData: "WIP",
          sepaAllowed: sepaAllowed,
          contractAccepted: contractAccepted,
          statuteAccepted: statuteAccepted,
          nbShares: selectedNumberOfCoopShares,
          pickupLocationId: selectedPickupLocation!.id!,
          shoppingCart: shoppingCart,
        },
      })
      .then((response) => {
        setCurrentStep("end");
        setConfirmOrderResponse(response);
      })
      .catch(handleRequestError)
      .finally(() => setConfirmOrderLoading(false));
  }

  function getNextButton() {
    if (currentStep === "summary") {
      return (
        <TapirButton
          icon={"check"}
          variant={"primary"}
          text={"Bestellung abschließen"}
          onClick={onConfirmOrder}
          iconPosition={"right"}
          loading={confirmOrderLoading}
        />
      );
    }

    const productType = publicProductTypes.find(
      (productType) => productType.id === currentStep,
    );
    if (productType !== undefined) {
      const buttonParams = buildNextButtonParametersForProductType(
        productType,
        shoppingCart,
        checkingCapacities,
      );
      return (
        <BestellWizardNextButton
          onNextClicked={onNextClicked}
          params={buttonParams}
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
        if (!statuteAccepted) {
          text = "Akzeptiere die Satzung um weiter zu gehen";
        }
        break;
      case "personal_data":
        if (!isPersonalDataValid(personalData)) {
          text = "Vervollständige deine Daten um weiter zu gehen";
        } else if (!sepaAllowed) {
          text = "Ermächtige das SEPA-Mandat um weiter zu gehen";
        } else if (!contractAccepted) {
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

  function setTestData() {
    setPersonalData(getTestPersonalData());
    setSelectedProductTypes(publicProductTypes);
    const newShoppingCart: ShoppingCart = {};
    for (const productType of publicProductTypes) {
      for (const product of productType.products) {
        newShoppingCart[product.id!] = 1;
      }
    }
    setShoppingCart(newShoppingCart);
    setSelectedPickupLocation(pickupLocations[0]);
    setSelectedNumberOfCoopShares(7);
    setSepaAllowed(true);
    setContractAccepted(true);
    setStatuteAccepted(true);
  }

  function confirmEnableWaitingListMode() {
    setWaitingListModeEnabled(true);
    setProductWaitingListModalOpen(false);
    goToNextStep();
  }

  function cancelEnableWaitingListMode() {
    setProductWaitingListModalOpen(false);
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
                <TapirButton
                  text={"Test-Daten für alle Schritte setzen"}
                  variant={"outline-warning"}
                  icon={"construction"}
                  onClick={setTestData}
                />
                {getNextButton()}
              </div>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
      <ProductWaitingListModal
        show={productWaitingListModalOpen}
        onHide={cancelEnableWaitingListMode}
        confirmEnableWaitingListMode={confirmEnableWaitingListMode}
      />
    </>
  );
};

export default BestellWizard;
