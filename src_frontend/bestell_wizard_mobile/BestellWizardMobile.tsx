import React, { useEffect, useState } from "react";
import { Col, ProgressBar, Row, Spinner } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import { BestellWizardApi } from "../api-client";
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

interface BestellWizardProps {
  csrfToken: string;
}

type Step =
  | "1a_welcome"
  | "1b_welcome_waiting_list"
  | "2_first_name"
  | "3_product_type_choice"
  | "loading";

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

  useEffect(() => {
    Promise.all([
      bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
    ])
      .then(([baseData]) => {
        const newSettings = buildSettings(baseData, []);
        setSettings(newSettings);
        setSettingsLoaded(true);
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
    document
      .getElementById(currentStep)
      ?.scrollIntoView({ behavior: "smooth" });
  }, [currentStep]);

  useEffect(() => {
    if (!settingsLoaded) return;
    const newSteps = buildSteps();
    setSteps(newSteps);
    setCurrentStep(newSteps[0]);
  }, [settings]);

  function buildSteps() {
    const newSteps: Step[] = [];
    newSteps.push(
      settings.forceWaitingList ? "1b_welcome_waiting_list" : "1a_welcome",
    );
    newSteps.push("2_first_name");
    if (settings.introEnabled) {
      newSteps.push("3_product_type_choice");
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
          />
        );
      case "3_product_type_choice":
        return (
          <Step3ProductTypesChoice
            goToNextStep={goToNextStep}
            settings={settings}
            firstName={personalData.firstName}
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
    }
  }

  return (
    <Row style={{ height: "100%" }}>
      <Col style={{ height: "100%" }}>
        <Row style={{ height: "10%" }}>
          <div
            style={{ width: "100%", height: "100%" }}
            className={"d-flex justify-content-center align-items-center"}
          >
            <img
              src={settings.logoUrl}
              alt={"Logo"}
              style={{ height: "70%" }}
            />
          </div>
        </Row>
        <Row
          style={{
            height: "80%",
            overflowY: "hidden",
          }}
          id={"scroll_container"}
        >
          {steps.map((step) => {
            return (
              <div key={step} id={step} style={{ height: "75vh" }}>
                {getStepComponent(step)}
              </div>
            );
          })}
        </Row>
        <Row style={{ height: "10%" }}>
          <div
            style={{ width: "100%", height: "100%", paddingBottom: "1rem" }}
            className={"d-flex flex-column justify-content-end"}
          >
            <div style={{ width: "100%", textAlign: "center" }}>
              Schritt {steps.indexOf(currentStep) + 1} von {steps.length}
            </div>
            <div className={"d-flex flex-row gap-2 align-items-center"}>
              <TapirButton
                size={"sm"}
                text={"zurück"}
                variant={"outline-secondary"}
                onClick={goToPreviousStep}
              />
              <ProgressBar
                now={(100 * (steps.indexOf(currentStep) + 1)) / steps.length}
                style={{ width: "100%" }}
              />
            </div>
          </div>
        </Row>
      </Col>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </Row>
  );
};

export default BestellWizardMobile;
