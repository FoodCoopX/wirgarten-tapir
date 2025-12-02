import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./steps/BestellWizardIntro.tsx";
import {
  Card,
  Col,
  ListGroup,
  OverlayTrigger,
  Row,
  Spinner,
  Tooltip,
} from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
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
  WaitingListEntryDetails,
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
import { buildFilteredShoppingCart } from "./utils/buildFilteredShoppingCart.ts";
import { areAllOrderedProductsInWaitingList } from "./utils/areAllOrderedProductsInWaitingList.ts";

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
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
  const [productTypesInWaitingList, setProductTypesInWaitingList] = useState<
    Set<PublicProductType>
  >(new Set<PublicProductType>());
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
  const [checkingCapacitiesController, setCheckingCapacitiesController] =
    useState<AbortController>();
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
  const [becomeMemberNow, setBecomeMemberNow] = useState<boolean | null>(null);

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

        const newSettings = buildSettings(baseData);
        setSettings(newSettings);

        personalData.paymentRhythm = baseData.defaultPaymentRhythm;
        setPersonalData(Object.assign({}, personalData));

        if (pickupLocations.length === 1) {
          setSelectedPickupLocations([pickupLocations[0]]);
        }

        setShoppingCart(buildEmptyShoppingCart(newSettings.productTypes));

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
      shoppingCart,
      selectedProductTypes,
      becomeMemberNow,
    );

    if (!newSteps.includes(currentStep)) {
      let index = steps.indexOf(currentStep);
      index = Math.min(index, newSteps.length - 1);
      setCurrentStep(newSteps[index]);
    }

    setSteps(newSteps);
  }, [selectedProductTypes, shoppingCart, settings, becomeMemberNow]);

  useEffect(() => {
    if (waitingListEntryDetails === undefined) {
      updateProductsAndProductTypesOverCapacity(
        shoppingCart,
        setProductIdsOverCapacity,
        setProductTypeIdsOverCapacity,
        setCheckingCapacities,
        setToastDatas,
        checkingCapacitiesController,
        setCheckingCapacitiesController,
      );
    }

    updateMinimumNumberOfShares(
      shoppingCart,
      productTypesInWaitingList,
      setMinimumNumberOfShares,
      setSelectedNumberOfCoopShares,
    );
  }, [shoppingCart]);

  useEffect(() => {
    if (
      settings.pickupLocations.length === 0 ||
      isShoppingCartEmpty(shoppingCart) ||
      waitingListEntryDetails !== undefined
    ) {
      return;
    }

    checkPickupLocationCapacities(
      settings.pickupLocations,
      shoppingCart,
      setPickupLocationsWithCapacityCheckLoading,
      setPickupLocationsWithCapacityFull,
      setToastDatas,
    );
  }, [settings, shoppingCart]);

  useEffect(() => {
    if (
      selectedPickupLocations.length === 0 ||
      isShoppingCartEmpty(shoppingCart)
    ) {
      return;
    }

    fetchFirstDeliveryDates(
      shoppingCart,
      (data) =>
        setFirstDeliveryDatesByProductType(
          data[selectedPickupLocations[0].id!],
        ),
      setToastDatas,
      waitingListEntryDetails?.id,
    );
  }, [selectedPickupLocations, shoppingCart]);

  useEffect(() => {
    if (waitingListEntryDetails !== undefined) return;

    if (settings.forceWaitingList) {
      setShowGeneralWaitingListModal(true);
      setProductTypesInWaitingList(new Set(settings.productTypes));
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
      setShoppingCart,
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

  useEffect(() => {
    setProductTypesInWaitingList(
      new Set(
        [...productTypesInWaitingList].filter(
          (productType) =>
            !shouldProductTypeBeRemovedFromWaitingList(productType),
        ),
      ),
    );
  }, [productTypeIdsOverCapacity, productIdsOverCapacity]);

  function shouldProductTypeBeRemovedFromWaitingList(
    productType: PublicProductType,
  ) {
    if (settings.forceWaitingList) {
      return false;
    }

    if (productType.forceWaitingList) {
      return false;
    }

    if (productTypeIdsOverCapacity.includes(productType.id!)) {
      return false;
    }

    for (const product of productType.products) {
      if (productIdsOverCapacity.includes(product.id!)) {
        return false;
      }
    }

    return true;
  }

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

    if (!isProductTypeOrdered(productType, shoppingCart)) {
      return false;
    }

    if (productTypesInWaitingList.has(productType)) {
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
        isProductTypeOrdered(productType, shoppingCart) &&
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
        buildFilteredShoppingCart(
          shoppingCart,
          false,
          productTypesInWaitingList,
        ),
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
            setShoppingCart={setShoppingCart}
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
            waitingListModeEnabled={areAllOrderedProductsInWaitingList(
              shoppingCart,
              productTypesInWaitingList,
            )}
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
            studentStatusEnabled={studentStatusEnabled}
            setStudentStatusEnabled={setStudentStatusEnabled}
            waitingListLinkConfirmationModeEnabled={
              waitingListEntryDetails !== undefined
            }
            settings={settings}
            becomeMemberNow={becomeMemberNow}
            shoppingCart={shoppingCart}
            productTypesInWaitingList={productTypesInWaitingList}
            setBecomeMemberNow={setBecomeMemberNow}
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
              shoppingCart,
              productTypesInWaitingList,
              becomeMemberNow,
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
            shoppingCart={shoppingCart}
          />
        );
      case "summary":
        return (
          <BestellWizardSummary
            shoppingCart={shoppingCart}
            productTypesInWaitingList={productTypesInWaitingList}
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            selectedPickupLocations={selectedPickupLocations}
            firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
            updateOrderFromSummary={updateOrderFromSummary}
            waitingListModeEnabled={isWaitingListModeEnabled(
              settings,
              shoppingCart,
              productTypesInWaitingList,
              becomeMemberNow,
            )}
            cancellationPolicyRead={cancellationPolicyRead}
            setCancellationPolicyRead={setCancellationPolicyRead}
            privacyPolicyRead={privacyPolicyRead}
            setPrivacyPolicyRead={setPrivacyPolicyRead}
            waitingListEntryDetails={waitingListEntryDetails}
            contractStartDate={contractStartDate}
            settings={settings}
            becomeMemberNow={becomeMemberNow}
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
            shoppingCart={shoppingCart}
            setShoppingCart={setShoppingCart}
            waitingListLinkConfirmationModeEnabled={
              waitingListEntryDetails !== undefined
            }
            settings={settings}
            productIdsOverCapacity={productIdsOverCapacity}
            productTypeIdsOverCapacity={productTypeIdsOverCapacity}
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
            birthdate: new Date("01.01.1990"),
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

    bestellWizardApi
      .bestellWizardBestellWizardConfirmOrderCreate({
        bestellWizardConfirmOrderRequestRequest: {
          personalData: {
            accountOwner: personalData.accountOwner,
            birthdate: new Date("01.01.1990"),
            city: personalData.city,
            country: personalData.country,
            email: personalData.email,
            iban: personalData.iban,
            firstName: personalData.firstName,
            lastName: personalData.firstName,
            phoneNumber: personalData.phoneNumber,
            postcode: personalData.postcode,
            street: personalData.street,
            street2: personalData.street2,
          },
          sepaAllowed: sepaAllowed,
          contractAccepted: contractAccepted,
          statuteAccepted: statuteAccepted,
          numberOfCoopShares: selectedNumberOfCoopShares,
          pickupLocationIds: selectedPickupLocations.map(
            (locations) => locations.id!,
          ),
          shoppingCartOrder: buildFilteredShoppingCart(
            shoppingCart,
            false,
            productTypesInWaitingList,
          ),
          shoppingCartWaitingList: buildFilteredShoppingCart(
            shoppingCart,
            true,
            productTypesInWaitingList,
          ),
          studentStatusEnabled: studentStatusEnabled,
          paymentRhythm: personalData.paymentRhythm,
          becomeMemberNow:
            !settings.forceWaitingList && becomeMemberNow !== false,
          privacyPolicyRead: privacyPolicyRead,
          cancellationPolicyRead: cancellationPolicyRead,
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
          shoppingCart,
          productTypesInWaitingList,
          becomeMemberNow,
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
            shoppingCart,
            productTypesInWaitingList,
            becomeMemberNow,
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
            shoppingCart,
            productTypesInWaitingList,
            becomeMemberNow,
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
            shoppingCart,
            productTypesInWaitingList,
            becomeMemberNow,
          ),
          emailAddressAlreadyInUse,
        );
        break;
      default:
        params = buildNextButtonParametersForProductType(
          settings.productTypes,
          shoppingCart,
          checkingCapacities,
          currentStep,
          productTypesInWaitingList,
          productTypeIdsOverCapacity,
          productIdsOverCapacity,
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
    setShoppingCart(newShoppingCart);
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
    productTypesInWaitingList.add(productType);
    setProductTypesInWaitingList(new Set(productTypesInWaitingList));

    setProductWaitingListModalOpen(false);
    goToNextStep();
  }

  function cancelEnableProductWaitingListMode() {
    setProductWaitingListModalOpen(false);
  }

  function confirmEnablePickupLocationWaitingListMode() {
    for (const productType of settings.productTypes) {
      if (productType.noDelivery) continue;

      productTypesInWaitingList.add(productType);
      setProductTypesInWaitingList(new Set(productTypesInWaitingList));
    }

    setPickupLocationWaitingListModalOpen(false);
  }

  function cancelEnablePickupLocationWaitingListMode() {
    setPickupLocationWaitingListModalOpen(false);

    for (const productType of settings.productTypes) {
      if (productType.noDelivery) continue;
      productTypesInWaitingList.add(productType);
    }
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
              {isAtLeastOneProductOrdered(shoppingCart) && (
                <ListGroup.Item className={"list-group-item-dark"}>
                  <Row>
                    {isAtLeastOneProductOrdered(
                      buildFilteredShoppingCart(
                        shoppingCart,
                        false,
                        productTypesInWaitingList,
                      ),
                    ) && (
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
                            {formatShoppingCart(
                              buildFilteredShoppingCart(
                                shoppingCart,
                                false,
                                productTypesInWaitingList,
                              ),
                              settings,
                            )}
                          </div>
                        </OverlayTrigger>
                      </Col>
                    )}
                    {isAtLeastOneProductOrdered(
                      buildFilteredShoppingCart(
                        shoppingCart,
                        true,
                        productTypesInWaitingList,
                      ),
                    ) && (
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
                              buildFilteredShoppingCart(
                                shoppingCart,
                                true,
                                productTypesInWaitingList,
                              ),
                              settings,
                            )}
                            {" (Wartelisten-Eintrag)"}
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
                <TapirButton
                  text={"Persönliche Daten setzen"}
                  variant={"outline-warning"}
                  icon={"construction"}
                  onClick={() => setPersonalData(getTestPersonalData())}
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
