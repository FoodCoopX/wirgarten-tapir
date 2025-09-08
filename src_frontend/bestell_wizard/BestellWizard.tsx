import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./steps/BestellWizardIntro.tsx";
import { Card, Col, ListGroup, OverlayTrigger, Row, Spinner, Tooltip } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { useApi } from "../hooks/useApi.ts";
import {
  BestellWizardApi,
  CoopApi,
  OrderConfirmationResponse,
  PickupLocationsApi,
  PublicPickupLocation,
  type PublicProductType,
  WaitingListApi,
  WaitingListEntryDetails
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
  buildNextButtonParametersForProductType
} from "./utils/buildNextButtonParameters.ts";
import BestellWizardNextButton from "./components/BestellWizardNextButton.tsx";
import ProductWaitingListModal from "./components/ProductWaitingListModal.tsx";
import { NextButtonParameters } from "./types/NextButtonParameters.ts";
import { isShoppingCartEmpty } from "./utils/isShoppingCartEmpty.ts";
import PickupLocationWaitingListModal from "./components/PickupLocationWaitingListModal.tsx";
import { updateProductsAndProductTypesOverCapacity } from "./utils/updateProductsAndProductTypesOverCapacity.ts";
import { updateMinimumNumberOfShares } from "./utils/updateMinimumNumberOfShares.ts";
import { checkPickupLocationCapacities } from "./utils/checkPickupLocationCapacities.ts";
import GeneralWaitingListModal from "./components/GeneralWaitingListModal.tsx";
import { fetchFirstDeliveryDates } from "./utils/fetchFirstDeliveryDates.ts";
import BestellWizardProgressIndicator from "./components/BestellWizardProgressIndicator.tsx";
import { BestellWizardStep } from "./types/BestellWizardStep.ts";
import { buildEmptyShoppingCart } from "./utils/buildEmptyShoppingCart.ts";
import { selectAllRequiredProductTypes } from "./utils/selectAllRequiredProductTypes.ts";
import { buildNextButtonForStepSummary } from "./utils/buildNextButtonForStepSummary.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import { BestellWizardSettings } from "./types/BestellWizardSettings.ts";
import { buildEmptySettings } from "./utils/buildEmptySettings.ts";
import { sortPickupLocationsByWaitingListWishes } from "./utils/sortPickupLocationsByWaitingListWishes.ts";
import { buildSettings } from "./utils/buildSettings.ts";
import { buildSteps } from "./utils/buildSteps.ts";
import { setDataFromWaitingListEntry } from "./utils/setDataFromWaitingListEntry.ts";
import { isProductTypeOrdered } from "./utils/isProductTypeOrdered.ts";
import { isAtLeastOneOrderedProductWithDelivery } from "./utils/isAtLeastOneOrderedProductWithDelivery.ts";
import { isWaitingListModeEnabled } from "./utils/isWaitingListModeEnabled.ts";
import { isAtLeastOneProductOrdered } from "./utils/isAtLeastOneProductOrdered.ts";
import { formatShoppingCart } from "./utils/formatShoppingCart.ts";

interface BestellWizardProps {
  csrfToken: string;
  waitingListEntryDetails?: WaitingListEntryDetails;
}

const BestellWizard: React.FC<BestellWizardProps> = ({
  csrfToken,
  waitingListEntryDetails,
}) => {
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const pickupLocationApi = useApi(PickupLocationsApi, csrfToken);
  const waitingListApi = useApi(WaitingListApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);

  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());

  // user input
  const [shoppingCartOrder, setShoppingCartOrder] = useState<ShoppingCart>({});
  const [shoppingCartWaitingList, setShoppingCartWaitingList] =
    useState<ShoppingCart>({});
  const [selectedPickupLocations, setSelectedPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );
  const [selectedNumberOfCoopShares, setSelectedNumberOfCoopShares] =
    useState(0);
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [contractAccepted, setContractAccepted] = useState(false);
  const [statuteAccepted, setStatuteAccepted] = useState(false);
  const [investingMembership, setInvestingMembership] = useState(false);
  const [cancellationPolicyRead, setCancellationPolicyRead] = useState(false);
  const [privacyPolicyRead, setPrivacyPolicyRead] = useState(false);
  const [studentStatusEnabled, setStudentStatusEnabled] = useState(false);

  // calculated states
  const [
    pickupLocationsWithCapacityCheckLoading,
    setPickupLocationsWithCapacityCheckLoading,
  ] = useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [pickupLocationsWithCapacityFull, setPickupLocationsWithCapacityFull] =
    useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [steps, setSteps] = useState<(string | BestellWizardStep)[]>(["intro"]);
  const [confirmOrderLoading, setConfirmOrderLoading] = useState(false);
  const [confirmOrderResponse, setConfirmOrderResponse] =
    useState<OrderConfirmationResponse>();
  const [checkingCapacities, setCheckingCapacities] = useState(false);
  const [productIdsOverCapacity, setProductIdsOverCapacity] = useState<
    string[]
  >([]);
  const [productTypeIdsOverCapacity, setProductTypeIdsOverCapacity] = useState<
    string[]
  >([]);
  const [productWaitingListModalOpen, setProductWaitingListModalOpen] =
    useState(false);
  const [
    pickupLocationWaitingListModalOpen,
    setPickupLocationWaitingListModalOpen,
  ] = useState(false);
  const [baseDataLoading, setBaseDataLoading] = useState(true);
  const [showGeneralWaitingListModal, setShowGeneralWaitingListModal] =
    useState(false);
  const [firstDeliveryDatesByProductType, setFirstDeliveryDatesByProductType] =
    useState<{ [key: string]: Date }>({});
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [emailAddressAlreadyInUse, setEmailAddressAlreadyInUse] =
    useState(false);
  const [emailAdresseAlreadyInUseIsKnown, setEmailAdresseAlreadyInUseIsKnown] =
    useState(false);
  const [emailAddressAlreadyInUseLoading, setEmailAddressAlreadyInUseLoading] =
    useState(false);
  const [contractStartDate, setContractStartDate] = useState(new Date());
  const [minimumNumberOfShares, setMinimumNumberOfShares] = useState(0);
  const [selectedProductTypes, setSelectedProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [currentStep, setCurrentStep] = useState<BestellWizardStep | string>(
    "intro",
  );

  useEffect(() => {
    setBaseDataLoading(true);

    Promise.all([
      bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
      pickupLocationApi.pickupLocationsPublicPickupLocationsList(),
      coopApi.coopApiMinimumNumberOfSharesRetrieve({
        productIds: [],
        quantities: [],
      }),
    ])
      .then(([baseData, pickupLocations, minNumberOfShares]) => {
        setMinimumNumberOfShares(minNumberOfShares.minimumNumberOfShares);

        pickupLocations.sort((a, b) => a.name.localeCompare(b.name));
        sortPickupLocationsByWaitingListWishes(
          pickupLocations,
          waitingListEntryDetails,
        );

        const newSettings = buildSettings(baseData, pickupLocations);
        setSettings(newSettings);

        personalData.paymentRhythm = baseData.defaultPaymentRhythm;
        setPersonalData(Object.assign({}, personalData));

        if (pickupLocations.length === 1) {
          setSelectedPickupLocations([pickupLocations[0]]);
        }

        setShoppingCartOrder(buildEmptyShoppingCart(newSettings.productTypes));

        selectAllRequiredProductTypes(
          newSettings.productTypes,
          selectedProductTypes,
          setSelectedProductTypes,
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verteilstationen",
          setToastDatas,
        ),
      )
      .finally(() => setBaseDataLoading(false));
  }, []);

  useEffect(() => {
    if (settings.productTypes.length === 0) return;

    let newSteps = buildSteps(
      settings,
      waitingListEntryDetails,
      shoppingCartOrder,
      shoppingCartWaitingList,
      selectedProductTypes,
    );

    if (!newSteps.includes(currentStep)) {
      let index = steps.indexOf(currentStep);
      index = Math.min(index, newSteps.length - 1);
      setCurrentStep(newSteps[index]);
    }

    setSteps(newSteps);
  }, [
    selectedProductTypes,
    shoppingCartOrder,
    shoppingCartWaitingList,
    settings,
  ]);

  useEffect(() => {
    if (waitingListEntryDetails === undefined) {
      updateProductsAndProductTypesOverCapacity(
        shoppingCartOrder,
        setProductIdsOverCapacity,
        setProductTypeIdsOverCapacity,
        setCheckingCapacities,
        setToastDatas,
      );
    }

    updateMinimumNumberOfShares(
      shoppingCartOrder,
      setMinimumNumberOfShares,
      setSelectedNumberOfCoopShares,
    );
  }, [shoppingCartOrder]);

  useEffect(() => {
    if (
      settings.pickupLocations.length === 0 ||
      isShoppingCartEmpty(shoppingCartOrder) ||
      waitingListEntryDetails !== undefined
    ) {
      return;
    }

    checkPickupLocationCapacities(
      settings.pickupLocations,
      shoppingCartOrder,
      setPickupLocationsWithCapacityCheckLoading,
      setPickupLocationsWithCapacityFull,
      setToastDatas,
    );
  }, [settings, shoppingCartOrder]);

  useEffect(() => {
    if (
      selectedPickupLocations.length === 0 ||
      isShoppingCartEmpty(shoppingCartOrder)
    ) {
      return;
    }

    fetchFirstDeliveryDates(
      selectedPickupLocations,
      shoppingCartOrder,
      setFirstDeliveryDatesByProductType,
      setToastDatas,
      waitingListEntryDetails?.id,
    );
  }, [selectedPickupLocations, shoppingCartOrder]);

  useEffect(() => {
    if (waitingListEntryDetails !== undefined) return;

    if (settings.forceWaitingList) {
      setShowGeneralWaitingListModal(true);
    }
  }, [settings]);

  useEffect(() => {
    if (!waitingListEntryDetails) {
      return;
    }

    setDataFromWaitingListEntry(
      waitingListEntryDetails,
      setCurrentStep,
      steps,
      settings,
      setSelectedProductTypes,
      setShoppingCartOrder,
      setSelectedPickupLocations,
      setPersonalData,
      setSelectedNumberOfCoopShares,
    );
  }, [waitingListEntryDetails, settings]);

  useEffect(() => {
    bestellWizardApi
      .bestellWizardApiNextContractStartDateRetrieve({
        waitingListEntryId: waitingListEntryDetails?.id,
      })
      .then((result) => {
        setContractStartDate(new Date(result));
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vertragsstart-Datum",
          setToastDatas,
        ),
      );
  }, [waitingListEntryDetails]);

  function onNextClicked() {
    if (shouldOpenProductWaitingListModal()) {
      setProductWaitingListModalOpen(true);
      return;
    }
    if (shouldOpenPickupLocationWaitingListModal()) {
      setPickupLocationWaitingListModalOpen(true);
      return;
    }
    goToNextStep();
  }
  function getCurrentProductType(): PublicProductType {
    return settings.productTypes.find(
      (productType) => productType.id === currentStep,
    )!;
  }

  function shouldOpenProductWaitingListModal() {
    const productType = settings.productTypes.find(
      (productType) => productType.id === currentStep,
    );
    if (productType === undefined) {
      return false;
    }

    if (!isProductTypeOrdered(productType, shoppingCartOrder)) {
      return false;
    }

    if (settings.forceWaitingList || productType.forceWaitingList) {
      return true;
    }

    if (productTypeIdsOverCapacity.includes(productType.id!)) {
      return true;
    }

    for (const product of productType.products) {
      if (
        Object.keys(shoppingCartOrder).includes(product.id!) &&
        shoppingCartOrder[product.id!] > 0 &&
        productIdsOverCapacity.includes(product.id!)
      ) {
        return true;
      }
    }

    return false;
  }

  function shouldOpenPickupLocationWaitingListModal() {
    if (currentStep !== "pickup_location") {
      return false;
    }

    if (
      !isAtLeastOneOrderedProductWithDelivery(
        shoppingCartOrder,
        settings.productTypes,
      )
    ) {
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
    if (settings.theme === undefined) {
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
            selectedProductTypes={selectedProductTypes}
            setSelectedProductTypes={setSelectedProductTypes}
            settings={settings}
            investingMembership={investingMembership}
            setInvestingMembership={setInvestingMembership}
            setShoppingCart={setShoppingCartOrder}
            waitingListLinkConfirmationModeEnabled={
              waitingListEntryDetails !== undefined
            }
          />
        );
      case "pickup_location":
        return (
          <BestellWizardPickupLocation
            settings={settings}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsWithCapacityCheckLoading={
              pickupLocationsWithCapacityCheckLoading
            }
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
            waitingListEntryDetails={waitingListEntryDetails}
            waitingListModeEnabled={
              settings.forceWaitingList ||
              !isAtLeastOneOrderedProductWithDelivery(
                shoppingCartOrder,
                settings.productTypes,
              )
            }
          />
        );
      case "coop_shares":
        return (
          <BestellWizardCoopShares
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            setSelectedNumberOfCoopShares={setSelectedNumberOfCoopShares}
            statuteAccepted={statuteAccepted}
            setStatuteAccepted={setStatuteAccepted}
            minimumNumberOfShares={minimumNumberOfShares}
            waitingListModeEnabled={isWaitingListModeEnabled(
              settings,
              shoppingCartOrder,
              shoppingCartWaitingList,
            )}
            studentStatusEnabled={studentStatusEnabled}
            setStudentStatusEnabled={setStudentStatusEnabled}
            waitingListLinkConfirmationModeEnabled={
              waitingListEntryDetails !== undefined
            }
            settings={settings}
          />
        );
      case "personal_data":
        return (
          <BestellWizardPersonalData
            personalData={personalData}
            setPersonalData={setPersonalData}
            sepaAllowed={sepaAllowed}
            setSepaAllowed={setSepaAllowed}
            contractAccepted={contractAccepted}
            setContractAccepted={setContractAccepted}
            waitingListModeEnabled={isWaitingListModeEnabled(
              settings,
              shoppingCartOrder,
              shoppingCartWaitingList,
            )}
            waitingListLinkConfirmationModeEnabled={
              waitingListEntryDetails !== undefined
            }
            setToastDatas={setToastDatas}
            emailAddressAlreadyInUse={emailAddressAlreadyInUse}
            setEmailAddressAlreadyInUse={setEmailAddressAlreadyInUse}
            emailAdresseAlreadyInUseIsKnown={emailAdresseAlreadyInUseIsKnown}
            setEmailAdresseAlreadyInUseIsKnown={
              setEmailAdresseAlreadyInUseIsKnown
            }
            emailAddressAlreadyInUseLoading={emailAddressAlreadyInUseLoading}
            setEmailAddressAlreadyInUseLoading={
              setEmailAddressAlreadyInUseLoading
            }
            waitingListEntryDetails={waitingListEntryDetails}
            settings={settings}
          />
        );
      case "summary":
        return (
          <BestellWizardSummary
            shoppingCart={shoppingCartOrder}
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            selectedPickupLocations={selectedPickupLocations}
            firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
            updateOrderFromSummary={updateOrderFromSummary}
            waitingListModeEnabled={isWaitingListModeEnabled(
              settings,
              shoppingCartOrder,
              shoppingCartWaitingList,
            )}
            cancellationPolicyRead={cancellationPolicyRead}
            setCancellationPolicyRead={setCancellationPolicyRead}
            privacyPolicyRead={privacyPolicyRead}
            setPrivacyPolicyRead={setPrivacyPolicyRead}
            waitingListEntryDetails={waitingListEntryDetails}
            contractStartDate={contractStartDate}
            settings={settings}
          />
        );
      case "end":
        return <BestellWizardEnd response={confirmOrderResponse!} />;
      default:
        const productType = settings.productTypes.find(
          (productType) => productType.id === currentStep,
        );
        if (productType === undefined) {
          return <div>Product type with id {currentStep} not found</div>;
        }
        return (
          <BestellWizardProductType
            productType={productType}
            shoppingCart={shoppingCartOrder}
            setShoppingCart={setShoppingCartOrder}
            waitingListLinkConfirmationModeEnabled={
              waitingListEntryDetails !== undefined
            }
          />
        );
    }
  }

  function onConfirmOrder() {
    setConfirmOrderLoading(true);

    if (waitingListEntryDetails !== undefined) {
      waitingListApi
        .waitingListApiPublicConfirmWaitingListEntryCreate({
          publicConfirmWaitingListEntryRequestRequest: {
            entryId: waitingListEntryDetails.id,
            linkKey: waitingListEntryDetails.linkKey!,
            accountOwner: personalData.accountOwner,
            contractAccepted: contractAccepted,
            iban: personalData.iban,
            sepaAllowed: sepaAllowed,
            birthdate: personalData.birthdate,
            numberOfCoopShares: selectedNumberOfCoopShares,
            paymentRhythm: personalData.paymentRhythm,
          },
        })
        .then((response) => {
          setCurrentStep("end");
          setConfirmOrderResponse(response);
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler bei der Bestätigung der Bestellung aus Warteliste-Eintrag",
            setToastDatas,
          ),
        )
        .finally(() => setConfirmOrderLoading(false));

      return;
    }

    if (
      isWaitingListModeEnabled(
        settings,
        shoppingCartOrder,
        shoppingCartWaitingList,
      )
    ) {
      waitingListApi
        .waitingListApiPublicWaitingListCreateEntryPotentialMemberCreate({
          publicWaitingListEntryNewMemberCreateRequest: {
            firstName: personalData.firstName,
            lastName: personalData.lastName,
            email: personalData.email,
            phoneNumber: personalData.phoneNumber,
            street: personalData.street,
            street2: personalData.street2,
            postcode: personalData.postcode,
            city: personalData.city,
            shoppingCart: shoppingCartOrder,
            pickupLocationIds: selectedPickupLocations.map(
              (pickupLocations) => pickupLocations.id!,
            ),
            numberOfCoopShares: selectedNumberOfCoopShares,
          },
        })
        .then((response) => {
          setCurrentStep("end");
          setConfirmOrderResponse(response);
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler bei der Erzeugung des Warteliste-Eintrags",
            setToastDatas,
          ),
        )
        .finally(() => setConfirmOrderLoading(false));

      return;
    }

    bestellWizardApi
      .bestellWizardBestellWizardConfirmOrderCreate({
        bestellWizardConfirmOrderRequestRequest: {
          personalData: personalData,
          sepaAllowed: sepaAllowed,
          contractAccepted: contractAccepted,
          statuteAccepted: statuteAccepted,
          numberOfCoopShares: selectedNumberOfCoopShares,
          pickupLocationIds: selectedPickupLocations.map(
            (locations) => locations.id!,
          ),
          shoppingCart: shoppingCartOrder,
          studentStatusEnabled: studentStatusEnabled,
          paymentRhythm: personalData.paymentRhythm,
          becomeMemberNow: true,
          waitingListShoppingCart: {},
        },
      })
      .then((response) => {
        setCurrentStep("end");
        setConfirmOrderResponse(response);
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler bei der Bestätigung der Bestellung",
          setToastDatas,
        );
      })
      .finally(() => setConfirmOrderLoading(false));
  }

  function getNextButton() {
    if (currentStep === "summary") {
      return buildNextButtonForStepSummary(
        privacyPolicyRead,
        isWaitingListModeEnabled(
          settings,
          shoppingCartOrder,
          shoppingCartWaitingList,
        ),
        cancellationPolicyRead,
        confirmOrderLoading,
        onConfirmOrder,
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
          isWaitingListModeEnabled(
            settings,
            shoppingCartOrder,
            shoppingCartWaitingList,
          ),
        );
        break;
      case "coop_shares":
        params = buildNextButtonParametersForCoopShares(
          statuteAccepted,
          selectedNumberOfCoopShares,
          minimumNumberOfShares,
          isWaitingListModeEnabled(
            settings,
            shoppingCartOrder,
            shoppingCartWaitingList,
          ),
          studentStatusEnabled,
        );
        break;
      case "personal_data":
        params = buildNextButtonParametersForPersonalData(
          personalData,
          sepaAllowed,
          contractAccepted,
          isWaitingListModeEnabled(
            settings,
            shoppingCartOrder,
            shoppingCartWaitingList,
          ),
          emailAddressAlreadyInUse,
        );
        break;
      default:
        params = buildNextButtonParametersForProductType(
          settings.productTypes,
          shoppingCartOrder,
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
    setSelectedProductTypes(settings.productTypes);
    const newShoppingCart: ShoppingCart = {};
    for (const productType of settings.productTypes) {
      for (const product of productType.products) {
        newShoppingCart[product.id!] = 1;
      }
    }
    setShoppingCartOrder(newShoppingCart);
    setSelectedPickupLocations([settings.pickupLocations[0]]);
    setSelectedNumberOfCoopShares(7);
    setSepaAllowed(true);
    setContractAccepted(true);
    setStatuteAccepted(true);
    setCancellationPolicyRead(true);
    setPrivacyPolicyRead(true);
  }

  function confirmEnableProductWaitingListMode() {
    const productType = getCurrentProductType();
    moveProductType(shoppingCartOrder, shoppingCartWaitingList, productType);
    setShoppingCartOrder(Object.assign({}, shoppingCartOrder));
    setShoppingCartWaitingList(Object.assign({}, shoppingCartWaitingList));

    setProductWaitingListModalOpen(false);
    goToNextStep();
  }

  function doesProductBelongsToProductType(
    productId: string,
    productType: PublicProductType,
  ) {
    for (const product of productType.products) {
      if (product.id === productId) {
        return true;
      }
    }
    return false;
  }

  function cancelEnableProductWaitingListMode() {
    setProductWaitingListModalOpen(false);
  }

  function confirmEnablePickupLocationWaitingListMode() {
    console.log(shoppingCartOrder);
    console.log(shoppingCartWaitingList);

    for (const productType of settings.productTypes) {
      if (productType.noDelivery) continue;

      moveProductType(shoppingCartOrder, shoppingCartWaitingList, productType);
    }

    console.log(shoppingCartOrder);
    console.log(shoppingCartWaitingList);
    setShoppingCartOrder(Object.assign({}, shoppingCartOrder));
    setShoppingCartWaitingList(Object.assign({}, shoppingCartWaitingList));
    setPickupLocationWaitingListModalOpen(false);
  }

  function moveProductType(
    from: ShoppingCart,
    to: ShoppingCart,
    productType: PublicProductType,
  ) {
    for (const [productId, quantity] of Object.entries(from)) {
      if (doesProductBelongsToProductType(productId, productType)) {
        to[productId] = quantity;
        from[productId] = 0;
      }
    }
  }

  function cancelEnablePickupLocationWaitingListMode() {
    setPickupLocationWaitingListModalOpen(false);
  }

  function confirmEnableGeneralWaitingListMode() {
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
              {waitingListEntryDetails !== undefined && (
                <ListGroup.Item className={"list-group-item-warning"}>
                  <div className={"text-center"}>
                    Warteliste-Zuteilung{" "}
                    {waitingListEntryDetails.memberAlreadyExists
                      ? "Bestandmitglied " +
                        waitingListEntryDetails.firstName +
                        " " +
                        waitingListEntryDetails.lastName
                      : "neues Mitglied"}
                  </div>
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
              {(isAtLeastOneProductOrdered(shoppingCartOrder) ||
                isAtLeastOneProductOrdered(shoppingCartWaitingList)) && (
                <ListGroup.Item className={"list-group-item-dark"}>
                  <Row>
                    {isAtLeastOneProductOrdered(shoppingCartOrder) && (
                      <Col>
                        <OverlayTrigger
                          overlay={
                            <Tooltip id={"tooltip shopping cart"}>
                              Im Warenkorb, wird bestellt.
                            </Tooltip>
                          }
                        >
                          <div className={"text-center"}>
                            <span className={"material-icons"}>
                              shopping_cart
                            </span>{" "}
                            {formatShoppingCart(shoppingCartOrder, settings)}
                          </div>
                        </OverlayTrigger>
                      </Col>
                    )}
                    {isAtLeastOneProductOrdered(shoppingCartWaitingList) && (
                      <Col>
                        <OverlayTrigger
                          overlay={
                            <Tooltip id={"tooltip waiting list"}>
                              Wird in der Warteliste eingetragen
                            </Tooltip>
                          }
                        >
                          <div className={"text-center"}>
                            <span className={"material-icons"}>
                              pending_actions
                            </span>{" "}
                            {formatShoppingCart(
                              shoppingCartWaitingList,
                              settings,
                            )}
                          </div>
                        </OverlayTrigger>
                      </Col>
                    )}
                  </Row>
                </ListGroup.Item>
              )}
            </ListGroup>
            <Card.Footer>
              <div className={"d-flex justify-content-between"}>
                <div className={"d-flex flex-row gap-2"}>
                  <TapirButton
                    icon={"first_page"}
                    variant={"outline-primary"}
                    onClick={() => {
                      setCurrentStep(steps[0]);
                    }}
                    disabled={currentStep === steps[0]}
                  />
                  <TapirButton
                    icon={"chevron_left"}
                    variant={"outline-primary"}
                    text={"Zurück"}
                    onClick={onBackClicked}
                    disabled={currentStep === steps[0]}
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
            productTypes={settings.productTypes}
          />
        </Col>
      </Row>
      <ProductWaitingListModal
        show={productWaitingListModalOpen}
        onHide={cancelEnableProductWaitingListMode}
        confirmEnableWaitingListMode={confirmEnableProductWaitingListMode}
        productType={settings.productTypes.find(
          (productType) => productType.id === currentStep,
        )}
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
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default BestellWizard;
