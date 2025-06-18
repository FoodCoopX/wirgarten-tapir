import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./steps/BestellWizardIntro.tsx";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Card, Col, Row, Spinner } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { useApi } from "../hooks/useApi.ts";
import {
  BestellWizardConfirmOrderResponse,
  CoopApi,
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
import { getTestPersonalData } from "./utils/getTestPersonalData.ts";
import BestellWizardEnd from "./steps/BestellWizardEnd.tsx";
import {
  buildNextButtonParametersForCoopShares,
  buildNextButtonParametersForIntro,
  buildNextButtonParametersForPersonalData,
  buildNextButtonParametersForPickupLocation,
  buildNextButtonParametersForProductType,
} from "./utils/buildNextButtonParameters.ts";
import BestellWizardNextButton from "./components/BestellWizardNextButton.tsx";
import ProductWaitingListModal from "./components/ProductWaitingListModal.tsx";
import { NextButtonParameters } from "./types/NextButtonParameters.ts";
import { isShoppingCartEmpty } from "./utils/isShoppingCartEmpty.ts";

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
  const coopApi = useApi(CoopApi, csrfToken);
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
  const [minimumNumberOfShares, setMinimumNumberOfShares] = useState(0);
  const [priceOfAShare, setPriceOfAShare] = useState(0);

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
      .then((pickupLocations) => {
        pickupLocations.sort((a, b) => {
          return a.name.localeCompare(b.name);
        });
        setPickupLocations(pickupLocations);
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
    if (isShoppingCartEmpty(shoppingCart)) {
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

    coopApi
      .coopApiMinimumNumberOfSharesRetrieve({
        productIds: Object.keys(shoppingCart),
        quantities: Object.values(shoppingCart),
      })
      .then((response) => {
        setMinimumNumberOfShares(response.minimumNumberOfShares);
        setPriceOfAShare(response.priceOfAShare);
        if (selectedNumberOfCoopShares < response.minimumNumberOfShares) {
          setSelectedNumberOfCoopShares(response.minimumNumberOfShares);
        }
      });
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
            shoppingCart={shoppingCart}
            waitingListModeEnabled={waitingListModeEnabled}
            csrfToken={csrfToken}
          />
        );
      case "coop_shares":
        return (
          <BestellWizardCoopShares
            theme={theme}
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            setSelectedNumberOfCoopShares={setSelectedNumberOfCoopShares}
            statuteAccepted={statuteAccepted}
            setStatuteAccepted={setStatuteAccepted}
            minimumNumberOfShares={minimumNumberOfShares}
            priceOfAShare={priceOfAShare}
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
      const params = {
        disabled: false,
        loading: confirmOrderLoading,
        text: "Bestellung abschließen",
        icon: "check",
      };
      return (
        <BestellWizardNextButton
          params={params}
          onNextClicked={onConfirmOrder}
        />
      );
    }

    let params: NextButtonParameters;

    switch (currentStep) {
      case "intro":
        params = buildNextButtonParametersForIntro(selectedProductTypes);
        break;
      case "pickup_location":
        params = buildNextButtonParametersForPickupLocation(
          selectedPickupLocation,
        );
        break;
      case "coop_shares":
        params = buildNextButtonParametersForCoopShares(
          statuteAccepted,
          selectedNumberOfCoopShares,
          minimumNumberOfShares,
        );
        break;
      case "personal_data":
        params = buildNextButtonParametersForPersonalData(
          personalData,
          sepaAllowed,
          contractAccepted,
        );
        break;
      default:
        params = buildNextButtonParametersForProductType(
          publicProductTypes,
          shoppingCart,
          checkingCapacities,
          currentStep,
        );
    }

    if (params.text === undefined) {
      params.text = "Weiter";
    }

    if (params.icon === undefined) {
      params.icon = "chevron_right";
    }
    return (
      <BestellWizardNextButton params={params} onNextClicked={onNextClicked} />
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
