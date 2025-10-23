import React, { useEffect, useState } from "react";
import { ProgressBar, Spinner } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import { BestellWizardApi, type PublicProductType } from "../api-client";
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
import Step4AProductTypeIntro from "./steps/Step4AProductTypeIntro.tsx";
import Step4BProductTypeOrder from "./steps/Step4BProductTypeOrder.tsx";
import { buildEmptyShoppingCart } from "../bestell_wizard/utils/buildEmptyShoppingCart.ts";
import { ShoppingCart } from "../bestell_wizard/types/ShoppingCart.ts";
import BestellWizardMobileHeader from "./BestellWizardMobileHeader.tsx";

interface BestellWizardProps {
  csrfToken: string;
}

type Step =
  | "1a_welcome"
  | "1b_welcome_waiting_list"
  | "2_first_name"
  | "3_product_type_choice"
  | "loading"
  | string;

const BestellWizardMobile: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [steps, setSteps] = useState<Step[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<Step>("loading");
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );
  const [selectedProductTypes, setSelectedProductTypes] = useState<
    PublicProductType[]
  >([]);
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
  const [investingMembership, setInvestingMembership] = useState(false);

  useEffect(() => {
    Promise.all([
      bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
    ])
      .then(([baseData]) => {
        const newSettings = buildSettings(baseData, []);
        setSettings(newSettings);
        setSettingsLoaded(true);
        setSelectedProductTypes(newSettings.productTypes);
        setShoppingCart(buildEmptyShoppingCart(newSettings.productTypes));
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
  }, [settings, selectedProductTypes]);

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

  function skipProductType(productType: PublicProductType) {
    setSelectedProductTypes(
      selectedProductTypes.filter((pt) => pt.id !== productType.id),
    );

    setCurrentStep(steps[steps.indexOf(currentStep) + 2]);
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
              <Step4AProductTypeIntro
                productType={productType}
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
              />
            );
        }
    }
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
        />
      </div>
      <div
        style={{
          height: "80dvh",
          width: "100%",
          overflowY: "hidden",
        }}
        id={"scroll_container"}
      >
        {steps.map((step) => {
          return (
            <div key={step} id={step} style={{ height: "80vh" }}>
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
          <div style={{ width: "100%", textAlign: "center" }}>
            Schritt {steps.indexOf(currentStep) + 1} von {steps.length}
          </div>
          <div
            className={"d-flex flex-row gap-2 align-items-center"}
            style={{ marginRight: "1rem", marginLeft: "1rem" }}
          >
            <TapirButton
              size={"sm"}
              icon={"first_page"}
              variant={"outline-secondary"}
              onClick={() => setCurrentStep(steps[0])}
            />
            <TapirButton
              size={"sm"}
              icon={"chevron_backward"}
              variant={"outline-secondary"}
              onClick={goToPreviousStep}
            />
            <ProgressBar
              now={(100 * (steps.indexOf(currentStep) + 1)) / steps.length}
              style={{ width: "100%" }}
            />
          </div>
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
