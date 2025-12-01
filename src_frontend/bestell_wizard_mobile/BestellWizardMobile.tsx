import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  BestellWizardApi,
  CoopApi,
  PublicPickupLocation,
  type PublicProductType,
} from "../api-client";
import { buildSettings } from "../bestell_wizard/utils/buildSettings.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { buildEmptySettings } from "../bestell_wizard/utils/buildEmptySettings.ts";
import { ToastData } from "../types/ToastData.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
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
import BestellWizardMobileHeader from "./components/BestellWizardMobileHeader.tsx";
import { isAtLeastOneOrderedProductWithDelivery } from "../bestell_wizard/utils/isAtLeastOneOrderedProductWithDelivery.ts";
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
import StepBase from "./components/StepBase.tsx";
import { getStepTitle } from "./utils/getStepTitle.ts";
import Step13Feedback from "./steps/Step13Feedback.tsx";
import Step14Confirmation from "./steps/Step14Confirmation.tsx";
import { getStepBackground } from "./utils/getStepBackground.ts";
import BestellWizardMobileFooter from "./components/BestellWizardMobileFooter.tsx";
import { getPhase } from "./utils/getPhase.ts";
import { getProductTypeFromStep } from "./utils/getProductTypeFromStep.ts";
import { CONTENT_HEIGHT, HEADER_HEIGHT } from "./utils/DIMENSIONS.ts";
import Step4DSolidarityContribution from "./steps/Step4DSolidarityContribution.tsx";

interface BestellWizardProps {
  csrfToken: string;
}

const BestellWizardMobile: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);

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

  useEffect(() => {
    Promise.all([
      bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
      coopApi.coopApiMinimumNumberOfSharesRetrieve({
        productIds: [],
        quantities: [],
      }),
      bestellWizardApi.bestellWizardApiNextContractStartDateRetrieve({
        waitingListEntryId: undefined,
      }),
    ])
      .then(([baseData, minNumberOfShares, contractStartDateAsString]) => {
        const newSettings = buildSettings(baseData);
        setSettings(newSettings);
        setSettingsLoaded(true);
        setSelectedProductTypes(newSettings.productTypes);
        setShoppingCart(buildEmptyShoppingCart(newSettings.productTypes));
        setMinimumNumberOfShares(minNumberOfShares.minimumNumberOfShares);

        personalData.paymentRhythm = baseData.defaultPaymentRhythm;
        setPersonalData(Object.assign({}, personalData));

        setContractStartDate(new Date(contractStartDateAsString));
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
    const newSteps = buildSteps();
    setSteps(newSteps);
    if (!newSteps.includes(currentStep)) {
      setCurrentStep(newSteps[0]);
    }
  }, [settings, selectedProductTypes, shoppingCart, studentStatusEnabled]);

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
    );
  }, [settings, shoppingCart]);

  useEffect(() => {
    updateMinimumNumberOfShares(
      shoppingCart,
      new Set(),
      setMinimumNumberOfShares,
      setSelectedNumberOfCoopShares,
    );
    console.warn(
      "useEffect updateMinimumNumberOfShares is missing the products in waiting list",
    );
  }, [shoppingCart]);

  useEffect(() => {
    fetchFirstDeliveryDates(
      shoppingCart,
      setFirstDeliveryDatesByPickupLocationAndProductType,
      setToastDatas,
      undefined,
    );
  }, [shoppingCart]);

  function buildSteps() {
    const newSteps: Step[] = [];
    newSteps.push(
      settings.forceWaitingList ? "1b_welcome_waiting_list" : "1a_welcome",
    );
    newSteps.push("2_first_name");
    if (settings.introEnabled) {
      newSteps.push("3_product_type_choice");
    }

    for (const productType of selectedProductTypes) {
      if (!productType.noDelivery) {
        newSteps.push(productType.id! + "_intro");
        newSteps.push(productType.id! + "_order");
      }
    }

    const atLeastOneProductWithoutDelivery =
      selectedProductTypes.filter((productType) => productType.noDelivery)
        .length > 0;
    if (!atLeastOneProductWithoutDelivery) {
      newSteps.push("4d_solidarity_contribution");
    }

    if (
      settings.pickupLocations.length > 0 &&
      isAtLeastOneOrderedProductWithDelivery(
        shoppingCart,
        settings.productTypes,
      )
    ) {
      newSteps.push("5a_pickup_location_intro");
      newSteps.push("5b_pickup_location_choice");
    }

    for (const productType of selectedProductTypes) {
      if (productType.noDelivery) {
        newSteps.push(productType.id! + "_intro");
        newSteps.push(productType.id! + "_order");
      }
    }

    if (atLeastOneProductWithoutDelivery) {
      newSteps.push("4d_solidarity_contribution");
    }

    if (settings.showCoopContent) {
      newSteps.push("6a_coop_intro");
      newSteps.push("6b_coop_shares");
    }

    newSteps.push("8_personal_data");
    newSteps.push("9_banking_data");
    newSteps.push("10_summary");
    newSteps.push("11_legal");
    newSteps.push("12_channel");
    if (settings.feedbackStepEnabled) {
      newSteps.push("13_feedback");
    }
    newSteps.push("14_confirmation");

    return newSteps;
  }

  function goToNextStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex + 1 >= steps.length) {
      return;
    }

    setCurrentStep(steps[steps.indexOf(currentStep) + 1]);
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
            active={currentStep === "2_first_name"}
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
      case "4d_solidarity_contribution":
        return (
          <Step4DSolidarityContribution
            settings={settings}
            goToNextStep={goToNextStep}
            setSolidarityContribution={setSolidarityContribution}
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
          />
        );
      case "8_personal_data":
        return (
          <Step8PersonalData
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
            active={currentStep === step}
            selectedPickupLocations={selectedPickupLocations}
            solidarityContribution={solidarityContribution}
            personalData={personalData}
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
          />
        );
      case "12_channel":
        return (
          <Step12Channel
            goToNextStep={goToNextStep}
            settings={settings}
            selectedDistributionChannels={selectedDistributionChannels}
            setSelectedDistributionChannels={setSelectedDistributionChannels}
          />
        );
      case "13_feedback":
        return (
          <Step13Feedback goToNextStep={goToNextStep} settings={settings} />
        );
      case "14_confirmation":
        return (
          <Step14Confirmation
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
      default:
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
              />
            );
        }
    }
  }

  function getTopPosition(step: Step) {
    if (step === currentStep) {
      return HEADER_HEIGHT + "dvh";
    }

    if (steps.indexOf(step) < steps.indexOf(currentStep)) {
      return -CONTENT_HEIGHT + "dvh";
    }

    return "100dvh";
  }

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: "50%",
        width: "100%",
        maxWidth: "1000px",
        height: "100dvh",
        transform: "translate(-50%, 0)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          height: HEADER_HEIGHT + "dvh",
          width: "100%",
        }}
      >
        <BestellWizardMobileHeader
          settings={settings}
          showShoppingCart={steps.findIndex((step) => step === currentStep) > 2}
          shoppingCart={shoppingCart}
          phases={phases}
          selectedPickupLocations={selectedPickupLocations}
          steps={steps}
          setCurrentStep={setCurrentStep}
          solidarityContribution={solidarityContribution}
        />
      </div>
      <div
        style={{
          height: CONTENT_HEIGHT + "dvh",
          width: "100%",
        }}
        id={"scroll_container"}
      >
        {steps.map((step) => {
          return (
            <div
              key={step}
              id={step}
              style={{
                height: CONTENT_HEIGHT + "dvh",
                transition: "all 0.3s ease-in-out",
                opacity: currentStep === step ? 1 : 0,
                position: "fixed",
                top: getTopPosition(step),
                width: "100%",
                pointerEvents: currentStep === step ? "auto" : "none",
              }}
            >
              <StepBase
                title={getStepTitle(step, settings)}
                firstName={personalData.firstName}
                active={step === currentStep}
                content={getStepComponent(step)}
                backgroundImageUrl={getStepBackground(step, settings)}
              />
            </div>
          );
        })}
      </div>
      {currentStep !== "loading" && (
        <BestellWizardMobileFooter
          steps={steps}
          currentStep={currentStep}
          setCurrentStep={setCurrentStep}
          settings={settings}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default BestellWizardMobile;
