import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  BestellWizardApi,
  CoopApi,
  OrderConfirmationResponse,
  PublicGrowingPeriod,
  PublicPickupLocation,
  type PublicProductType,
  PublicWaitingListEntryDetails,
  WaitingListApi,
} from "../api-client";
import { buildSettings } from "../bestell_wizard/utils/buildSettings.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { buildEmptySettings } from "../bestell_wizard/utils/buildEmptySettings.ts";
import { ToastData } from "../types/ToastData.ts";
import Step3ProductTypesChoice from "./steps/Step3ProductTypesChoice.tsx";
import Step1AWelcome from "./steps/Step1AWelcome.tsx";
import Step2FirstName from "./steps/Step2FirstName.tsx";
import { PersonalData } from "../bestell_wizard/types/PersonalData.ts";
import { getEmptyPersonalData } from "../bestell_wizard/utils/getEmptyPersonalData.ts";
import Step1BWelcome from "./steps/Step1BWelcome.tsx";
import "../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import Step4BProductTypeOrder from "./steps/Step4BProductTypeOrder.tsx";
import { buildEmptyShoppingCart } from "../bestell_wizard/utils/buildEmptyShoppingCart.ts";
import { ShoppingCart } from "../bestell_wizard/types/ShoppingCart.ts";
import Step5BPickupLocationChoice from "./steps/Step5BPickupLocationChoice.tsx";
import { isShoppingCartEmpty } from "../bestell_wizard/utils/isShoppingCartEmpty.ts";
import { checkPickupLocationCapacities } from "../bestell_wizard/utils/checkPickupLocationCapacities.ts";
import { Phase } from "./types/Phase.ts";
import StepGenericIntro from "./steps/StepGenericIntro.tsx";
import Step6BCoopShares from "./steps/Step6BCoopShares.tsx";
import { updateMinimumNumberOfShares } from "../bestell_wizard/utils/updateMinimumNumberOfShares.ts";
import Step8PersonalData from "./steps/Step8PersonalData.tsx";
import Step9BankingData from "./steps/Step9BankingData.tsx";
import Step10OrderSummary from "./steps/Step10OrderSummary.tsx";
import { fetchFirstDeliveryDates } from "../bestell_wizard/utils/fetchFirstDeliveryDates.ts";
import Step11Legal from "./steps/Step11Legal.tsx";
import { Step } from "./types/Step.ts";
import Step12Channel from "./steps/Step12Channel.tsx";
import Step13Feedback from "./steps/Step13Feedback.tsx";
import Step14Confirmation from "./steps/Step14Confirmation.tsx";
import { getPhase } from "./utils/getPhase.ts";
import { getProductTypeFromStep } from "./utils/getProductTypeFromStep.ts";
import Step7SolidarityContribution from "./steps/Step7SolidarityContribution.tsx";
import { getTestPersonalData } from "../bestell_wizard/utils/getTestPersonalData.ts";
import { updateProductsAndProductTypesOverCapacity } from "../bestell_wizard/utils/updateProductsAndProductTypesOverCapacity.ts";
import { buildSteps } from "./utils/buildSteps.ts";
import Step6CCoopMemberNow from "./steps/Step6CCoopMemberNow.tsx";
import Step5CPickupLocationConfirmWaitingList from "./steps/Step5CPickupLocationConfirmWaitingList.tsx";
import { PickupLocationTab } from "./types/PickupLocationTab.ts";
import { isAtLeastOneProductOrdered } from "../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import Step14BConfirmationWaitingList from "./steps/Step14BConfirmationWaitingList.tsx";
import Step3BGrowingPeriodChoice from "./steps/Step3BGrowingPeriodChoice.tsx";
import { updateProductPrices } from "../utils/updateProductPrices.ts";
import { buildFilteredShoppingCart } from "../bestell_wizard/utils/buildFilteredShoppingCart.ts";
import { areAllOrderedProductsInWaitingList } from "../bestell_wizard/utils/areAllOrderedProductsInWaitingList.ts";
import { addToast } from "../utils/addToast.ts";
import { v4 as uuidv4 } from "uuid";
import { updateWaitingList } from "./utils/updateWaitingList.ts";
import BestellWizardMobileBase from "./components/BestellWizardMobileBase.tsx";
import { sortProductTypes } from "../bestell_wizard/utils/sortProductTypes.ts";
import { getProductTypeByProductId } from "./utils/getProductTypeByProductId.ts";
import { getPublicPickupLocationById } from "./utils/getPublicPickupLocationById.ts";

interface BestellWizardMobileProps {
  csrfToken: string;
  waitingListEntryDetails?: PublicWaitingListEntryDetails;
}

const BestellWizardMobile: React.FC<BestellWizardMobileProps> = ({
  csrfToken,
  waitingListEntryDetails,
}) => {
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const waitingListApi = useApi(WaitingListApi, csrfToken);

  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [steps, setSteps] = useState<Step[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<Step>("loading");
  const [phases, setPhases] = useState<Phase[]>([]);
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );
  const [selectedProductTypes, setSelectedProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
  const [investingMembership, setInvestingMembership] = useState(false);

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
  const [statuteAccepted, setStatuteAccepted] = useState(false);
  const [minimumNumberOfShares, setMinimumNumberOfShares] = useState(0);
  const [studentStatusEnabled, setStudentStatusEnabled] = useState(false);
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [contractAccepted, setContractAccepted] = useState(false);
  const [contractStartDate, setContractStartDate] = useState(new Date());
  const [
    firstDeliveryDatesByPickupLocationAndProductType,
    setFirstDeliveryDatesByPickupLocationAndProductType,
  ] = useState<{ [key: string]: { [key: string]: Date } }>({});
  const [cancellationPolicyRead, setCancellationPolicyRead] = useState(false);
  const [privacyPolicyRead, setPrivacyPolicyRead] = useState(false);
  const [selectedDistributionChannels, setSelectedDistributionChannels] =
    useState<Set<string>>(new Set<string>());
  const [solidarityContribution, setSolidarityContribution] = useState(0);
  const [emailAddressAlreadyInUse, setEmailAddressAlreadyInUse] =
    useState(false);
  const [emailAddressAlreadyInUseLoading, setEmailAddressAlreadyInUseLoading] =
    useState(false);
  const [checkingCapacities, setCheckingCapacities] = useState(false);
  const [checkingCapacitiesController, setCheckingCapacitiesController] =
    useState<AbortController>();
  const [productIdsOverCapacity, setProductIdsOverCapacity] = useState<
    string[]
  >([]);
  const [productTypeIdsOverCapacity, setProductTypeIdsOverCapacity] = useState<
    string[]
  >([]);
  const [productTypesInWaitingList, setProductTypesInWaitingList] = useState<
    Set<PublicProductType>
  >(new Set<PublicProductType>());
  const [becomeMemberNow, setBecomeMemberNow] = useState<boolean | null>(null);
  const [currentPickupLocationTab, setCurrentPickupLocationTab] =
    useState<PickupLocationTab>("map");
  const [selectedGrowingPeriod, setSelectedGrowingPeriod] =
    useState<PublicGrowingPeriod>();
  const [productPricesController, setProductPricesController] =
    useState<AbortController>();
  const [confirmOrderLoading, setConfirmOrderLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
      coopApi.coopApiMinimumNumberOfSharesRetrieve({
        productIds: [],
        quantities: [],
      }),
    ])
      .then(([baseData, minNumberOfShares]) => {
        const newSettings = buildSettings(baseData);
        setSettings(newSettings);
        setSettingsLoaded(true);
        setSelectedProductTypes(
          newSettings.introEnabled ? [] : newSettings.productTypes,
        );
        if (waitingListEntryDetails) {
          setShoppingCart(
            buildShoppingCartFromWaitingListEntry(
              newSettings,
              waitingListEntryDetails,
              setSelectedProductTypes,
            ),
          );
        } else {
          setShoppingCart(buildEmptyShoppingCart(newSettings.productTypes));
        }
        setMinimumNumberOfShares(minNumberOfShares.minimumNumberOfShares);

        personalData.paymentRhythm = baseData.defaultPaymentRhythm;

        if (waitingListEntryDetails) {
          personalData.firstName = waitingListEntryDetails.firstName;
          personalData.lastName = waitingListEntryDetails.lastName;
          personalData.email = waitingListEntryDetails.email;
          personalData.phoneNumber = waitingListEntryDetails.phoneNumber;
          personalData.street = waitingListEntryDetails.street;
          personalData.street2 = waitingListEntryDetails.street2;
          personalData.postcode = waitingListEntryDetails.postcode;
          personalData.city = waitingListEntryDetails.city;
          personalData.iban = waitingListEntryDetails.iban ?? "";
          personalData.accountOwner =
            waitingListEntryDetails.accountOwner ?? "";
          personalData.paymentRhythm =
            waitingListEntryDetails.paymentRhythm ??
            baseData.defaultPaymentRhythm;

          setSelectedPickupLocations(
            (waitingListEntryDetails.pickupLocationWishes ?? [])
              .map((pickupLocation) =>
                getPublicPickupLocationById(pickupLocation.id!, newSettings),
              )
              .filter((pl) => pl !== undefined),
          );
        }

        setPersonalData({ ...personalData });

        if (newSettings.growingPeriodChoices.length > 0) {
          setSelectedGrowingPeriod(newSettings.growingPeriodChoices[0]);
        }

        setSolidarityContribution(settings.solidarityContributionDefault);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der BestellWizard",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    if (!selectedGrowingPeriod) {
      return;
    }

    updateProductPrices(
      selectedGrowingPeriod,
      productPricesController,
      setProductPricesController,
      settings,
      setSettings,
      setToastDatas,
    );

    setContractStartDate(selectedGrowingPeriod.contractStartDate);
  }, [selectedGrowingPeriod]);

  useEffect(() => {
    function handleBeforeUnload(event: BeforeUnloadEvent) {
      if (
        isAtLeastOneProductOrdered(shoppingCart) &&
        currentStep !== steps.at(-1)
      ) {
        event.preventDefault();
      }
    }

    addEventListener("beforeunload", handleBeforeUnload);

    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [shoppingCart, currentStep]);

  useEffect(() => {
    const element = document.getElementById(currentStep);
    element?.scrollIntoView({
      behavior: "smooth",
    });
  }, [currentStep, steps]);

  function onWindowResize() {
    const element = document.getElementById(currentStep);
    element?.scrollIntoView({
      behavior: "instant",
    });
  }

  useEffect(() => {
    window.addEventListener("resize", onWindowResize, { capture: false });
  }, [onWindowResize]);

  useEffect(() => {
    if (!settingsLoaded) return;
    const newSteps = buildSteps(
      settings,
      selectedProductTypes,
      shoppingCart,
      becomeMemberNow,
      productTypesInWaitingList,
      selectedPickupLocations,
      pickupLocationsWithCapacityFull,
      waitingListEntryDetails,
    );

    setSteps(newSteps);
    if (waitingListEntryDetails) {
      const index = newSteps.indexOf("2_first_name");
      setCurrentStep(newSteps[index + 1]);
    } else if (!newSteps.includes(currentStep)) {
      setCurrentStep(newSteps[0]);
    }
  }, [
    settings,
    selectedProductTypes,
    shoppingCart,
    studentStatusEnabled,
    becomeMemberNow,
    productTypesInWaitingList,
    selectedPickupLocations,
    pickupLocationsWithCapacityFull,
    waitingListEntryDetails,
  ]);

  useEffect(() => {
    const newPhases: Phase[] = [];
    for (const step of steps) {
      const stepPhase = getPhase(step);
      if (!newPhases.includes(stepPhase)) {
        newPhases.push(stepPhase);
      }
    }
    setPhases(newPhases);
  }, [steps, currentStep, shoppingCart, settings]);

  useEffect(() => {
    if (
      settings.pickupLocations.length === 0 ||
      isShoppingCartEmpty(shoppingCart)
    ) {
      return;
    }

    checkPickupLocationCapacities(
      settings.pickupLocations,
      shoppingCart,
      setPickupLocationsWithCapacityCheckLoading,
      setPickupLocationsWithCapacityFull,
      setToastDatas,
      selectedGrowingPeriod,
    );
  }, [settings, shoppingCart, selectedGrowingPeriod]);

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
        selectedGrowingPeriod,
      );
    }

    updateMinimumNumberOfShares(
      shoppingCart,
      productTypesInWaitingList,
      setMinimumNumberOfShares,
      setSelectedNumberOfCoopShares,
    );
  }, [shoppingCart, selectedGrowingPeriod]);

  useEffect(() => {
    if (!selectedGrowingPeriod) {
      return;
    }

    fetchFirstDeliveryDates(
      shoppingCart,
      selectedGrowingPeriod,
      setFirstDeliveryDatesByPickupLocationAndProductType,
      setToastDatas,
      undefined,
    );
  }, [shoppingCart, selectedGrowingPeriod]);

  useEffect(() => {
    updateWaitingList(
      selectedPickupLocations,
      pickupLocationsWithCapacityFull,
      settings,
      shoppingCart,
      productTypeIdsOverCapacity,
      productIdsOverCapacity,
      setProductTypesInWaitingList,
    );
  }, [
    productTypeIdsOverCapacity,
    productIdsOverCapacity,
    pickupLocationsWithCapacityFull,
    selectedPickupLocations,
    shoppingCart,
  ]);

  useEffect(() => {
    setBecomeMemberNow(null);
  }, [shoppingCart]);

  function buildShoppingCartFromWaitingListEntry(
    settings: BestellWizardSettings,
    waitingListEntryDetails: PublicWaitingListEntryDetails,
    setSelectedProductTypes: (types: PublicProductType[]) => void,
  ) {
    const newShoppingCart = buildEmptyShoppingCart(settings.productTypes);
    const selectedProductTypes = new Set<PublicProductType>();
    for (const wish of waitingListEntryDetails.productWishes ?? []) {
      newShoppingCart[wish.product.id!] = wish.quantity;

      const publicProductType = getProductTypeByProductId(
        wish.product.id!,
        settings,
      );
      if (publicProductType) {
        selectedProductTypes.add(publicProductType);
      }
    }
    setSelectedProductTypes(sortProductTypes([...selectedProductTypes]));
    return newShoppingCart;
  }

  function goToNextStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex + 1 >= steps.length) {
      return;
    }

    setCurrentStep(steps[steps.indexOf(currentStep) + 1]);
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

  function onConfirmOrder() {
    setConfirmOrderLoading(true);

    if (waitingListEntryDetails !== undefined) {
      waitingListApi
        .waitingListApiPublicConfirmWaitingListEntryCreate({
          publicConfirmWaitingListEntryRequestRequest: {
            entryId: waitingListEntryDetails.entryId,
            accountOwner: personalData.accountOwner,
            contractAccepted:
              contractAccepted || waitingListEntryDetails.memberAlreadyExists,
            iban: personalData.iban,
            sepaAllowed:
              sepaAllowed || waitingListEntryDetails.memberAlreadyExists,
            linkKey: waitingListEntryDetails.linkKey,
            numberOfCoopShares: selectedNumberOfCoopShares,
            paymentRhythm: personalData.paymentRhythm,
            solidarityContribution: solidarityContribution,
          },
        })
        .then(handleOrderResponse)
        .catch(async (error) => {
          await handleRequestError(
            error,
            "Fehler bei der Bestätigung der Warteliste-Eintrag",
            setToastDatas,
          );
        })
        .finally(() => setConfirmOrderLoading(false));
      return;
    }

    bestellWizardApi
      .bestellWizardBestellWizardConfirmOrderCreate({
        bestellWizardConfirmOrderRequestRequest: {
          personalData: {
            accountOwner: personalData.accountOwner,
            city: personalData.city,
            country: personalData.country,
            email: personalData.email,
            iban: personalData.iban,
            firstName: personalData.firstName,
            lastName: personalData.lastName,
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
          growingPeriodId: selectedGrowingPeriod!.id!,
          solidarityContribution: solidarityContribution,
          distributionChannels: [...selectedDistributionChannels],
        },
      })
      .then(handleOrderResponse)
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler bei der Bestätigung der Bestellung",
          setToastDatas,
        );
      })
      .finally(() => setConfirmOrderLoading(false));
  }

  function handleOrderResponse(response: OrderConfirmationResponse) {
    if (!response.orderConfirmed) {
      addToast(
        {
          title: "Fehler beim Bestellen",
          message: response.error ?? undefined,
          variant: "danger",
          id: uuidv4(),
        },
        setToastDatas,
      );
      return;
    }

    if (
      areAllOrderedProductsInWaitingList(
        shoppingCart,
        productTypesInWaitingList,
      ) &&
      becomeMemberNow === false
    ) {
      setCurrentStep("14b_confirmation_waiting_list");
    } else {
      setCurrentStep("14_confirmation");
    }
  }

  function getStepComponent(step: Step) {
    switch (step) {
      case "1a_welcome":
        return (
          <Step1AWelcome goToNextStep={goToNextStep} settings={settings} />
        );
      case "1b_welcome_waiting_list":
        return (
          <Step1BWelcome goToNextStep={goToNextStep} settings={settings} />
        );
      case "2_first_name":
        return (
          <Step2FirstName
            goToNextStep={goToNextStep}
            personalData={personalData}
            setPersonalData={setPersonalData}
            settings={settings}
            active={currentStep === step}
          />
        );
      case "3_product_type_choice":
        return (
          <Step3ProductTypesChoice
            goToNextStep={goToNextStep}
            settings={settings}
            firstName={personalData.firstName}
            selectedProductTypes={selectedProductTypes}
            setSelectedProductTypes={setSelectedProductTypes}
            investingMembership={investingMembership}
            setInvestingMembership={setInvestingMembership}
            setShoppingCart={setShoppingCart}
          />
        );
      case "3b_growing_period_choice":
        return (
          <Step3BGrowingPeriodChoice
            goToNextStep={goToNextStep}
            settings={settings}
            selectedGrowingPeriod={selectedGrowingPeriod}
            setSelectedGrowingPeriod={setSelectedGrowingPeriod}
          />
        );
      case "5a_pickup_location_intro":
        return (
          <StepGenericIntro
            content={{
              text: settings.strings.step5aText,
            }}
            goToNextStep={goToNextStep}
          />
        );
      case "5b_pickup_location_choice":
        return (
          <Step5BPickupLocationChoice
            settings={settings}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsWithCapacityCheckLoading={
              pickupLocationsWithCapacityCheckLoading
            }
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            goToNextStep={goToNextStep}
            stepIsActive={step === "5b_pickup_location_choice"}
            firstDeliveryDatesByPickupLocationAndProductType={
              firstDeliveryDatesByPickupLocationAndProductType
            }
            active={currentStep === step}
            productTypesInWaitingList={productTypesInWaitingList}
            shoppingCart={shoppingCart}
            currentTab={currentPickupLocationTab}
            setCurrentTab={setCurrentPickupLocationTab}
            productTypeIdsOverCapacity={productTypeIdsOverCapacity}
            productIdsOverCapacity={productIdsOverCapacity}
            isOrderStep={false}
            orderLoading={false}
            changesDisabled={
              (waitingListEntryDetails?.pickupLocationWishes ?? []).length > 0
            }
          />
        );
      case "5c_pickup_location_confirm_waiting_list":
        return (
          <Step5CPickupLocationConfirmWaitingList
            settings={settings}
            setCurrentStep={setCurrentStep}
            goToNextStep={goToNextStep}
            setCurrentTab={setCurrentPickupLocationTab}
          />
        );
      case "6a_coop_intro":
        return (
          <StepGenericIntro
            goToNextStep={goToNextStep}
            content={{
              text: settings.strings.step6aText,
            }}
          />
        );
      case "6b_coop_shares":
        return (
          <Step6BCoopShares
            goToNextStep={goToNextStep}
            settings={settings}
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            setSelectedNumberOfCoopShares={setSelectedNumberOfCoopShares}
            minimumNumberOfShares={minimumNumberOfShares}
            studentStatusEnabled={studentStatusEnabled}
            setStudentStatusEnabled={setStudentStatusEnabled}
            statuteAccepted={statuteAccepted}
            setStatuteAccepted={setStatuteAccepted}
            active={currentStep === step}
            isOrderStep={false}
            orderLoading={false}
            canChangeNumberOfShares={
              !waitingListEntryDetails?.memberAlreadyExists
            }
            forceHideStudentCheckbox={!isAtLeastOneProductOrdered(shoppingCart)}
          />
        );
      case "6c_coop_member_now":
        return (
          <Step6CCoopMemberNow
            settings={settings}
            setCurrentStep={setCurrentStep}
            setBecomeMemberNow={setBecomeMemberNow}
          />
        );
      case "7_solidarity_contribution":
        return (
          <Step7SolidarityContribution
            settings={settings}
            goToNextStep={goToNextStep}
            setSolidarityContribution={setSolidarityContribution}
            solidarityContribution={solidarityContribution}
            active={currentStep === step}
            shoppingCart={shoppingCart}
            productTypesInWaitingList={productTypesInWaitingList}
          />
        );
      case "8_personal_data":
        return (
          <Step8PersonalData
            settings={settings}
            goToNextStep={goToNextStep}
            personalData={personalData}
            setPersonalData={setPersonalData}
            active={currentStep === step}
            emailAddressAlreadyInUse={emailAddressAlreadyInUse}
            setEmailAddressAlreadyInUse={setEmailAddressAlreadyInUse}
            emailAddressAlreadyInUseLoading={emailAddressAlreadyInUseLoading}
            setEmailAddressAlreadyInUseLoading={
              setEmailAddressAlreadyInUseLoading
            }
            setToastDatas={setToastDatas}
            changesDisabled={waitingListEntryDetails !== undefined}
          />
        );
      case "9_banking_data":
        return (
          <Step9BankingData
            goToNextStep={goToNextStep}
            personalData={personalData}
            setPersonalData={setPersonalData}
            sepaAllowed={sepaAllowed}
            setSepaAllowed={setSepaAllowed}
            contractAccepted={contractAccepted}
            setContractAccepted={setContractAccepted}
            settings={settings}
            shoppingCart={shoppingCart}
            solidarityContribution={solidarityContribution}
            active={currentStep === step}
            productTypesInWaitingList={productTypesInWaitingList}
            isOrderStep={false}
            orderLoading={false}
            canChangePaymentRhythm={true}
          />
        );
      case "10_summary":
        return (
          <Step10OrderSummary
            goToNextStep={goToNextStep}
            settings={settings}
            studentStatusEnabled={studentStatusEnabled}
            numberOfCoopShares={selectedNumberOfCoopShares}
            shoppingCart={shoppingCart}
            contractStartDate={contractStartDate}
            firstDeliveryDatesByPickupLocationAndProductType={
              firstDeliveryDatesByPickupLocationAndProductType
            }
            goToProductTypeStep={(productType) => {
              if (!selectedProductTypes.includes(productType)) {
                setSelectedProductTypes([...selectedProductTypes, productType]);
              }
              setCurrentStep(productType.id + "_order");
            }}
            selectedPickupLocations={selectedPickupLocations}
            solidarityContribution={solidarityContribution}
            personalData={personalData}
            productTypesInWaitingList={productTypesInWaitingList}
            becomeMemberNow={becomeMemberNow}
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            confirmOrderLoading={confirmOrderLoading}
            isOrderStep={waitingListEntryDetails !== undefined}
            confirmOrder={onConfirmOrder}
            waitingListEntryDetails={waitingListEntryDetails}
          />
        );
      case "11_legal":
        return (
          <Step11Legal
            goToNextStep={goToNextStep}
            settings={settings}
            cancellationPolicyRead={cancellationPolicyRead}
            setCancellationPolicyRead={setCancellationPolicyRead}
            privacyPolicyRead={privacyPolicyRead}
            setPrivacyPolicyRead={setPrivacyPolicyRead}
            active={step === currentStep}
            productTypesInWaitingList={productTypesInWaitingList}
            shoppingCart={shoppingCart}
            solidarityContribution={solidarityContribution}
          />
        );
      case "12_channel":
        return (
          <Step12Channel
            goToNextStep={goToNextStep}
            settings={settings}
            selectedDistributionChannels={selectedDistributionChannels}
            setSelectedDistributionChannels={setSelectedDistributionChannels}
            confirmOrder={
              settings.feedbackStepEnabled ? undefined : onConfirmOrder
            }
            confirmOrderLoading={
              settings.feedbackStepEnabled ? false : confirmOrderLoading
            }
          />
        );
      case "13_feedback":
        return (
          <Step13Feedback
            goToNextStep={goToNextStep}
            settings={settings}
            confirmOrder={onConfirmOrder}
            confirmOrderLoading={confirmOrderLoading}
          />
        );
      case "14_confirmation":
        return (
          <Step14Confirmation
            settings={settings}
            memberMail={personalData.email}
          />
        );
      case "14b_confirmation_waiting_list":
        return (
          <Step14BConfirmationWaitingList
            settings={settings}
            memberMail={personalData.email}
          />
        );
      case "loading":
        return (
          <div
            style={{ width: "100%", height: "100%" }}
            className={"d-flex justify-content-center align-items-center"}
          >
            <Spinner />
          </div>
        );
      default: {
        // If the step is not one of the predefined ones, then it's a product type step
        const [productType, subStep] = getProductTypeFromStep(step, settings);
        if (productType === undefined) {
          return <div>Fehler: ungültiges Schritt {step}</div>;
        }
        switch (subStep) {
          case "intro":
            return (
              <StepGenericIntro
                content={{
                  text: productType.descriptionBestellwizardLong,
                  accordions: productType.accordions,
                }}
                goToNextStep={goToNextStep}
              />
            );
          case "order":
            return (
              <Step4BProductTypeOrder
                settings={settings}
                productType={productType}
                goToNextStep={goToNextStep}
                shoppingCart={shoppingCart}
                setShoppingCart={setShoppingCart}
                active={step === currentStep}
                checkingCapacities={checkingCapacities}
                productTypeIdsOverCapacity={productTypeIdsOverCapacity}
                productIdsOverCapacity={productIdsOverCapacity}
                waitingListLinkConfirmationModeEnabled={
                  waitingListEntryDetails !== undefined
                }
                productTypesInWaitingList={productTypesInWaitingList}
                isOrderStep={false}
                orderLoading={false}
              />
            );
        }
      }
    }
  }

  return (
    <BestellWizardMobileBase
      settings={settings}
      steps={steps}
      currentStep={currentStep}
      setCurrentStep={setCurrentStep}
      shoppingCart={shoppingCart}
      phases={phases}
      selectedPickupLocations={selectedPickupLocations}
      solidarityContribution={solidarityContribution}
      productTypesInWaitingList={productTypesInWaitingList}
      personalData={personalData}
      getStepComponent={getStepComponent}
      setTestData={setTestData}
      toastDatas={toastDatas}
      setToastDatas={setToastDatas}
      showProgress={true}
      hideFooterButtonsOnLastStep={true}
      selectedNumberOfCoopShares={selectedNumberOfCoopShares}
    />
  );
};

export default BestellWizardMobile;
