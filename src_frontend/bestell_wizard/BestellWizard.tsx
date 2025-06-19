import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./steps/BestellWizardIntro.tsx";
import { TapirTheme } from "../types/TapirTheme.ts";
import { Card, Col, ListGroup, Row, Spinner } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { useApi } from "../hooks/useApi.ts";
import {
  BestellWizardConfirmOrderResponse,
  PickupLocationsApi,
  PublicPickupLocation,
  type PublicProductType,
  SubscriptionsApi,
} from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BestellWizardProductType from "./steps/BestellWizardProductType.tsx";
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
import PickupLocationWaitingListModal from "./components/PickupLocationWaitingListModal.tsx";
import { updateProductsAndProductTypesOverCapacity } from "./utils/updateProductsAndProductTypesOverCapacity.ts";
import { updateMinimumAndPriceOfShare } from "./utils/updateMinimumAndPriceOfShare.ts";
import { checkPickupLocationCapacities } from "./utils/checkPickupLocationCapacities.ts";
import { sortProductTypes } from "./utils/sortProductTypes.ts";
import GeneralWaitingListModal from "./components/GeneralWaitingListModal.tsx";
import { fetchFirstDeliveryDates } from "./utils/fetchFirstDeliveryDates.ts";
import { isAtLeastOneOrderedProductWithDelivery } from "./utils/isAtLeastOneOrderedProductWithDelivery.ts";
import BestellWizardProgressIndicator from "./components/BestellWizardProgressIndicator.tsx";
import { BestellWizardStep } from "./types/BestellWizardStep.ts";
import { buildEmptyShoppingCart } from "./types/buildEmptyShoppingCart.ts";
import { selectedAllRequiredProductTypes } from "./utils/selectedAllRequiredProductTypes.ts";

interface BestellWizardProps {
  csrfToken: string;
}

const BestellWizard: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  const [theme, setTheme] = useState<TapirTheme>();
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
  const [selectedPickupLocations, setSelectedPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [
    pickupLocationsWithCapacityCheckLoading,
    setPickupLocationsWithCapacityCheckLoading,
  ] = useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [pickupLocationsWithCapacityFull, setPickupLocationsWithCapacityFull] =
    useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
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
  const [
    pickupLocationWaitingListModalOpen,
    setPickupLocationWaitingListModalOpen,
  ] = useState(false);
  const [minimumNumberOfShares, setMinimumNumberOfShares] = useState(0);
  const [priceOfAShare, setPriceOfAShare] = useState(0);
  const [allowInvestingMembership, setAllowInvestingMembership] =
    useState(false);
  const [forceWaitingList, setForceWaitingList] = useState(false);
  const [baseDataLoading, setBaseDataLoading] = useState(true);
  const [showGeneralWaitingListModal, setShowGeneralWaitingListModal] =
    useState(false);
  const [firstDeliveryDatesByProductType, setFirstDeliveryDatesByProductType] =
    useState<{ [key: string]: Date }>({});
  const [investingMembership, setInvestingMembership] = useState(false);

  useEffect(() => {
    setBaseDataLoading(true);
    subscriptionsApi
      .subscriptionsApiBestellWizardBaseDataRetrieve()
      .then((data) => {
        setTheme(data.theme as TapirTheme);
        setPublicProductTypes(sortProductTypes(data.productTypes));
        setPriceOfAShare(data.priceOfAShare);
        setAllowInvestingMembership(data.allowInvestingMembership);
        setForceWaitingList(data.forceWaitingList);
      })
      .catch(handleRequestError)
      .finally(() => setBaseDataLoading(false));

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
    setShoppingCart(buildEmptyShoppingCart(publicProductTypes));

    selectedAllRequiredProductTypes(
      publicProductTypes,
      selectedProductTypes,
      setSelectedProductTypes,
    );
  }, [publicProductTypes]);

  useEffect(() => {
    let steps = [
      "intro",
      ...selectedProductTypes.map((productType) => productType.id!),
      "pickup_location",
      "coop_shares",
      "personal_data",
      "summary",
      "end",
    ];

    if (
      !isAtLeastOneOrderedProductWithDelivery(shoppingCart, publicProductTypes)
    ) {
      steps = steps.filter((step) => step !== "pickup_location");
    }

    setSteps(steps);
  }, [selectedProductTypes, shoppingCart]);

  useEffect(() => {
    updateProductsAndProductTypesOverCapacity(
      shoppingCart,
      setProductIdsOverCapacity,
      setProductTypeIdsOverCapacity,
      setCheckingCapacities,
    );

    updateMinimumAndPriceOfShare(
      shoppingCart,
      setMinimumNumberOfShares,
      selectedNumberOfCoopShares,
      setSelectedNumberOfCoopShares,
    );
  }, [shoppingCart]);

  useEffect(() => {
    if (forceWaitingList) {
      setWaitingListModeEnabled(true);
      return;
    }
    if (
      productIdsOverCapacity.length === 0 &&
      productTypeIdsOverCapacity.length === 0 &&
      selectedPickupLocations.length > 0 &&
      pickupLocationsWithCapacityCheckLoading.size === 0 &&
      !pickupLocationsWithCapacityFull.has(selectedPickupLocations[0])
    ) {
      setWaitingListModeEnabled(false);
    }
  }, [
    forceWaitingList,
    productIdsOverCapacity,
    productTypeIdsOverCapacity,
    selectedPickupLocations,
    pickupLocationsWithCapacityCheckLoading,
    pickupLocationsWithCapacityFull,
  ]);

  useEffect(() => {
    if (pickupLocations.length === 0 || isShoppingCartEmpty(shoppingCart)) {
      return;
    }

    checkPickupLocationCapacities(
      pickupLocations,
      shoppingCart,
      setPickupLocationsWithCapacityCheckLoading,
      setPickupLocationsWithCapacityFull,
    );
  }, [pickupLocations, shoppingCart]);

  useEffect(() => {
    if (
      selectedPickupLocations.length === 0 ||
      isShoppingCartEmpty(shoppingCart)
    ) {
      return;
    }

    fetchFirstDeliveryDates(
      selectedPickupLocations,
      shoppingCart,
      setFirstDeliveryDatesByProductType,
    );
  }, [selectedPickupLocations, shoppingCart]);

  useEffect(() => {
    if (forceWaitingList) {
      setShowGeneralWaitingListModal(true);
      setWaitingListModeEnabled(true);
    }
  }, [forceWaitingList]);

  function onNextClicked() {
    if (!waitingListModeEnabled && shouldOpenProductWaitingListModal()) {
      setProductWaitingListModalOpen(true);
      return;
    }
    if (!waitingListModeEnabled && shouldOpenPickupLocationWaitingListModal()) {
      setPickupLocationWaitingListModalOpen(true);
      return;
    }
    goToNextStep();
  }

  function shouldOpenProductWaitingListModal() {
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

  function shouldOpenPickupLocationWaitingListModal() {
    if (currentStep !== "pickup_location") {
      return false;
    }

    if (pickupLocationsWithCapacityFull.has(selectedPickupLocations[0])) {
      return true;
    }
  }

  function goToNextStep() {
    setCurrentStep(steps[steps.indexOf(currentStep) + 1]);
  }

  function onBackClicked() {
    setCurrentStep(steps[steps.indexOf(currentStep) - 1]);
  }

  function updateOrderFromSummary(productType: PublicProductType) {
    if (!selectedProductTypes.includes(productType)) {
      setSelectedProductTypes([...selectedProductTypes, productType]);
    }
    setCurrentStep(productType.id!);
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
            allowInvestingMembership={allowInvestingMembership}
            investingMembership={investingMembership}
            setInvestingMembership={setInvestingMembership}
            setShoppingCart={setShoppingCart}
          />
        );
      case "pickup_location":
        return (
          <BestellWizardPickupLocation
            theme={theme}
            pickupLocations={pickupLocations}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            waitingListModeEnabled={waitingListModeEnabled}
            pickupLocationsWithCapacityCheckLoading={
              pickupLocationsWithCapacityCheckLoading
            }
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
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
            waitingListModeEnabled={waitingListModeEnabled}
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
            waitingListModeEnabled={waitingListModeEnabled}
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
            selectedPickupLocations={selectedPickupLocations}
            priceOfAShare={priceOfAShare}
            firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
            updateOrderFromSummary={updateOrderFromSummary}
            waitingListModeEnabled={waitingListModeEnabled}
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
          pickupLocationId: selectedPickupLocations[0].id!,
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
        text: waitingListModeEnabled
          ? "Warteliste-Eintrag bestätigen"
          : "Bestellung abschließen",
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
        params = buildNextButtonParametersForIntro(
          selectedProductTypes,
          investingMembership,
        );
        break;
      case "pickup_location":
        params = buildNextButtonParametersForPickupLocation(
          selectedPickupLocations,
          pickupLocationsWithCapacityCheckLoading,
        );
        break;
      case "coop_shares":
        params = buildNextButtonParametersForCoopShares(
          statuteAccepted,
          selectedNumberOfCoopShares,
          minimumNumberOfShares,
          waitingListModeEnabled,
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
    setSelectedPickupLocations([pickupLocations[0]]);
    setSelectedNumberOfCoopShares(7);
    setSepaAllowed(true);
    setContractAccepted(true);
    setStatuteAccepted(true);
  }

  function confirmEnableProductWaitingListMode() {
    setWaitingListModeEnabled(true);
    setProductWaitingListModalOpen(false);
    goToNextStep();
  }

  function cancelEnableProductWaitingListMode() {
    setProductWaitingListModalOpen(false);
  }

  function confirmEnablePickupLocationWaitingListMode() {
    setWaitingListModeEnabled(true);
    setPickupLocationWaitingListModalOpen(false);
  }

  function cancelEnablePickupLocationWaitingListMode() {
    setPickupLocationWaitingListModalOpen(false);
  }

  function confirmEnableGeneralWaitingListMode() {
    setWaitingListModeEnabled(true);
    setShowGeneralWaitingListModal(false);
  }

  return (
    <>
      <Row className={"justify-content-center p-4"}>
        <Col style={{ maxWidth: "1200px" }}>
          <Card style={{ height: "95vh" }}>
            <Card.Header>
              {baseDataLoading ? (
                <div className={"d-flex justify-content-center"}>
                  <Spinner />
                </div>
              ) : (
                <h2 className={"text-center mb-0"}>Biotop Oberland eG</h2>
              )}
            </Card.Header>
            <ListGroup
              variant={"flush"}
              style={{
                overflowX: "hidden",
                height: "100%",
              }}
            >
              {waitingListModeEnabled && (
                <ListGroup.Item className={"list-group-item-warning"}>
                  <div className={"text-center"}>Warteliste-Eintrag</div>
                </ListGroup.Item>
              )}
              <ListGroup.Item
                style={{
                  height: "100%",
                  overflowY: "scroll",
                  overflowX: "hidden",
                }}
              >
                {baseDataLoading ? (
                  <div
                    className={
                      "d-flex justify-content-center flex-column align-items-center"
                    }
                    style={{ width: "100%", height: "100%" }}
                  >
                    <Spinner style={{ width: "10rem", height: "10rem" }} />
                  </div>
                ) : (
                  <div
                    style={{
                      width: "100%",
                      height: "100%",
                      overflowY: "scroll",
                      overflowX: "hidden",
                    }}
                  >
                    {buildCurrentStepComponent()}
                  </div>
                )}
              </ListGroup.Item>
            </ListGroup>
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
        <Col style={{ width: "50px", flexGrow: 0.1 }}>
          <BestellWizardProgressIndicator
            currentStep={currentStep}
            steps={steps}
            productTypes={publicProductTypes}
          />
        </Col>
      </Row>
      <ProductWaitingListModal
        show={productWaitingListModalOpen}
        onHide={cancelEnableProductWaitingListMode}
        confirmEnableWaitingListMode={confirmEnableProductWaitingListMode}
      />
      <PickupLocationWaitingListModal
        show={pickupLocationWaitingListModalOpen}
        onHide={cancelEnablePickupLocationWaitingListMode}
        confirmEnableWaitingListMode={
          confirmEnablePickupLocationWaitingListMode
        }
      />
      <GeneralWaitingListModal
        show={showGeneralWaitingListModal}
        confirmEnableWaitingListMode={confirmEnableGeneralWaitingListMode}
      />
    </>
  );
};

export default BestellWizard;
