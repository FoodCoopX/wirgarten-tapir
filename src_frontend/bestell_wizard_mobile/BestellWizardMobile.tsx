import React, { useEffect, useState } from "react";
import { Form, ProgressBar, Spinner } from "react-bootstrap";
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
import TapirButton from "../components/TapirButton.tsx";
import Step1AWelcome from "./steps/Step1AWelcome.tsx";
import Step2FirstName from "./steps/Step2FirstName.tsx";
import { PersonalData } from "../bestell_wizard/types/PersonalData.ts";
import { getEmptyPersonalData } from "../bestell_wizard/utils/getEmptyPersonalData.ts";
import Step1BWelcome from "./steps/Step1BWelcome.tsx";
import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import Step4BProductTypeOrder from "./steps/Step4BProductTypeOrder.tsx";
import { buildEmptyShoppingCart } from "../bestell_wizard/utils/buildEmptyShoppingCart.ts";
import { ShoppingCart } from "../bestell_wizard/types/ShoppingCart.ts";
import BestellWizardMobileHeader from "./BestellWizardMobileHeader.tsx";
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
  const [currentPhase, setCurrentPhase] = useState<Phase>("loading");
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );
  const [selectedProductTypes, setSelectedProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
  const [investingMembership, setInvestingMembership] = useState(false);
  const [debugPhases, setDebugPhases] = useState(false);

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
  const [firstDeliveryDatesByProductType, setFirstDeliveryDatesByProductType] =
    useState<{ [key: string]: Date }>({});
  const [cancellationPolicyRead, setCancellationPolicyRead] = useState(false);
  const [privacyPolicyRead, setPrivacyPolicyRead] = useState(false);
  const [selectedDistributionChannels, setSelectedDistributionChannels] =
    useState<Set<string>>(new Set<string>());

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
    setCurrentPhase(getPhase(currentStep));
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
      setToastDatas,
      undefined,
    );
  }, [selectedPickupLocations, shoppingCart]);

  function getPhase(step: Step): Phase {
    switch (step) {
      case "loading":
        return "loading";
      case "1a_welcome":
      case "1b_welcome_waiting_list":
      case "2_first_name":
        return "intro";
      case "5a_pickup_location_intro":
      case "5b_pickup_location_choice":
        return "pickup_location";
      case "6a_coop_intro":
      case "6b_coop_shares":
        return "coop";
      case "8_personal_data":
      case "9_banking_data":
      case "10_summary":
      case "11_legal":
        return "personal_data";
      case "12_channel":
      case "13_feedback":
        return "feedback";
      case "14_confirmation":
        return "confirmation";

      default:
        const separatorIndex = step.lastIndexOf("_");
        if (separatorIndex == -1) {
          alert("Missing phase for step " + step);
          return "unknown";
        }
        return step.slice(0, separatorIndex);
    }
  }

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
      newSteps.push(productType.id! + "_intro");
      newSteps.push(productType.id! + "_order");
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

    if (settings.showCoopContent) {
      newSteps.push("6a_coop_intro");
      newSteps.push("6b_coop_shares");
    }

    newSteps.push("8_personal_data");
    newSteps.push("9_banking_data");
    newSteps.push("10_summary");
    newSteps.push("11_legal");
    newSteps.push("12_channel");
    newSteps.push("13_feedback");
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

  function goToPreviousStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex - 1 < 0) {
      return;
    }

    setCurrentStep(steps[steps.indexOf(currentStep) - 1]);
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
      case "5a_pickup_location_intro":
        return (
          <StepGenericIntro
            content={{
              title: settings.strings.step5aTitle,
              text: settings.strings.step5aText,
            }}
            goToNextStep={goToNextStep}
            active={step === currentStep}
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
          />
        );
      case "6a_coop_intro":
        return (
          <StepGenericIntro
            goToNextStep={goToNextStep}
            content={{
              title: settings.strings.step6aTitle,
              text: settings.strings.step6aText,
            }}
            active={step === currentStep}
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
            firstName={personalData.firstName}
            active={step === currentStep}
          />
        );
      case "8_personal_data":
        return (
          <Step8PersonalData
            goToNextStep={goToNextStep}
            personalData={personalData}
            setPersonalData={setPersonalData}
            settings={settings}
            active={step === currentStep}
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
            active={step === currentStep}
          />
        );
      case "10_summary":
        return (
          <Step10OrderSummary
            goToNextStep={goToNextStep}
            personalData={personalData}
            settings={settings}
            studentStatusEnabled={studentStatusEnabled}
            numberOfCoopShares={selectedNumberOfCoopShares}
            shoppingCart={shoppingCart}
            contractStartDate={contractStartDate}
            firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
            goToProductTypeStep={(productType) => {
              if (!selectedProductTypes.includes(productType)) {
                setSelectedProductTypes([...selectedProductTypes, productType]);
              }
              setCurrentStep(productType.id + "_order");
            }}
            active={currentStep === step}
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
            firstName={personalData.firstName}
          />
        );
      case "12_channel":
        return (
          <Step12Channel
            goToNextStep={goToNextStep}
            settings={settings}
            active={step === currentStep}
            firstName={personalData.firstName}
            selectedDistributionChannels={selectedDistributionChannels}
            setSelectedDistributionChannels={setSelectedDistributionChannels}
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
        const separatorIndex = step.lastIndexOf("_");
        const productId = step.slice(0, separatorIndex);
        const subStep = step.slice(separatorIndex + 1);
        const productType = settings.productTypes.find(
          (productType) => productType.id === productId,
        );
        if (productType === undefined) {
          return <div>Fehler: ungültiges Schritt {step}</div>;
        }
        switch (subStep) {
          case "intro":
            return (
              <StepGenericIntro
                content={{
                  title: "Unser " + productType.name,
                  text: productType.descriptionBestellwizardLong,
                  accordions: productType.accordions,
                }}
                goToNextStep={goToNextStep}
                active={step === currentStep}
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
              />
            );
        }
    }
  }

  function getPhaseName(phase: Phase) {
    for (const productType of settings.productTypes) {
      if (productType.id === phase) {
        return productType.name;
      }
    }

    return phase;
  }

  function getTopPosition(step: Step) {
    if (step === currentStep) {
      return "10dvh";
    }

    if (steps.indexOf(step) < steps.indexOf(currentStep)) {
      return "-80dvh";
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
          height: "10dvh",
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
        />
      </div>
      <div
        style={{
          height: "80dvh",
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
                height: "80dvh",
                transition: "all 0.3s ease-in-out",
                opacity: currentStep === step ? 1 : 0,
                position: "fixed",
                top: getTopPosition(step),
                width: "100%",
                pointerEvents: currentStep === step ? "auto" : "none",
              }}
            >
              {getStepComponent(step)}
            </div>
          );
        })}
      </div>
      <div
        style={{
          height: "10dvh",
          width: "100%",
        }}
      >
        <div
          style={{ width: "100%", height: "100%", paddingBottom: "1rem" }}
          className={"d-flex flex-column justify-content-end"}
        >
          <small
            style={{ width: "100%", textAlign: "center" }}
            className={"d-flex flex-row justify-content-center gap-2"}
          >
            <span>
              Schritt {phases.indexOf(currentPhase) + 1} von {phases.length}
            </span>
            <Form.Check
              checked={debugPhases}
              onChange={(event) => setDebugPhases(event.target.checked)}
            />
            {debugPhases && <span>Debug enabled</span>}
          </small>
          {debugPhases && (
            <small
              className={
                "d-flex flex-row gap-2 justify-content-center flex-wrap"
              }
              style={{ lineHeight: "1.1rem" }}
            >
              {phases.map((phase) => (
                <span className={currentPhase === phase ? "fw-bold" : ""}>
                  {getPhaseName(phase)}
                </span>
              ))}
            </small>
          )}
          {currentStep !== "loading" && (
            <div
              className={"d-flex flex-row gap-2 align-items-center"}
              style={{ marginRight: "1rem", marginLeft: "1rem" }}
            >
              <TapirButton
                size={"sm"}
                icon={"chevron_line_up"}
                variant={"outline-secondary"}
                onClick={() => setCurrentStep(steps[0])}
              />
              <TapirButton
                size={"sm"}
                icon={"keyboard_arrow_up"}
                variant={"outline-secondary"}
                onClick={goToPreviousStep}
              />
              <ProgressBar
                now={(100 * (steps.indexOf(currentStep) + 1)) / steps.length}
                style={{ width: "100%" }}
              />
            </div>
          )}
        </div>
      </div>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default BestellWizardMobile;
