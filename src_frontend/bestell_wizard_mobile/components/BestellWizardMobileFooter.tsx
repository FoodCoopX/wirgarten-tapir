import React from "react";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { Step } from "../types/Step.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { getPhase } from "../utils/getPhase.ts";
import { Badge, Dropdown, DropdownButton, ProgressBar } from "react-bootstrap";
import { Phase } from "../types/Phase.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { FOOTER_HEIGHT } from "../utils/DIMENSIONS.ts";
import "./footer.css";

interface BestellWizardMobileFooterProps {
  steps: Step[];
  currentStep: Step;
  setCurrentStep: (step: Step) => void;
  settings: BestellWizardSettings;
  setTestData: () => void;
}

const BestellWizardMobileFooter: React.FC<BestellWizardMobileFooterProps> = ({
  steps,
  currentStep,
  setCurrentStep,
  settings,
  setTestData,
}) => {
  function goToPreviousStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex - 1 < 0) {
      return;
    }

    setCurrentStep(steps[steps.indexOf(currentStep) - 1]);
  }

  function isStepFirstInPhase(step: Step, index: number) {
    const stepPhase = getPhase(step);
    for (let i = 0; i < index; i++) {
      if (getPhase(steps[i]) == stepPhase) {
        return false;
      }
    }
    return true;
  }

  function getPhaseName(phase: Phase) {
    switch (phase) {
      case "intro":
        return "Intro";
      case "coop":
        return "Genossenschaft";
      case "pickup_location":
        return "Verteilstation";
      case "solidarity":
        return "Solibeitrag";
      case "personal_data":
        return "Persönliche Daten";
      case "feedback":
        return "Feedback";
      case "confirmation":
        return "Bestätigung";
    }

    for (const productType of settings.productTypes) {
      if (productType.id === phase) {
        return productType.name;
      }
    }

    return phase;
  }

  function isProgressBarStepClickable(step: Step) {
    return steps.indexOf(step) < steps.indexOf(currentStep);
  }

  function getStepName(step: string) {
    for (const productType of settings.productTypes) {
      step = step.replace(productType.id!, productType.name);
    }
    return step;
  }

  return (
    <div
      style={{
        height: FOOTER_HEIGHT + "dvh",
        width: "100%",
      }}
    >
      <div
        style={{ width: "auto", height: "100%", paddingBottom: "0.5rem" }}
        className={"d-flex flex-column justify-content-end gap-2 mx-2"}
      >
        {currentStep !== steps[steps.length - 1] && (
          <div
            className={
              "d-flex flex-row gap-2 align-items-center justify-content-center"
            }
          >
            <TapirButton
              size={"sm"}
              icon={"chevron_line_up"}
              variant={BUTTON_VARIANT}
              onClick={() => setCurrentStep(steps[0])}
              text={"Zum Start"}
            />
            <TapirButton
              size={"sm"}
              icon={"keyboard_arrow_up"}
              variant={BUTTON_VARIANT}
              onClick={goToPreviousStep}
              text={"Zurück"}
            />
            <DropdownButton
              title={
                <span>
                  <span
                    style={{ fontSize: "16px" }}
                    className={"material-icons"}
                  >
                    construction
                  </span>
                  Test
                </span>
              }
              size={"sm"}
              variant={BUTTON_VARIANT}
              drop={"up"}
            >
              {steps
                .slice()
                .reverse()
                .map((step) => (
                  <Dropdown.Item
                    key={step}
                    onClick={() => setCurrentStep(step)}
                    style={{ lineHeight: "1rem" }}
                  >
                    <small>{getStepName(step)}</small>
                  </Dropdown.Item>
                ))}
              <Dropdown.Divider />
              <Dropdown.Item onClick={setTestData}>
                Test daten setzen
              </Dropdown.Item>
            </DropdownButton>
          </div>
        )}
        <small
          className={
            "d-flex flex-row flex-wrap gap-1 justify-content-center align-items-center"
          }
          style={{ width: "100%" }}
          id={"footer_widescreen"}
        >
          {steps.map((step, index) =>
            isStepFirstInPhase(step, index) ? (
              <Badge
                bg={
                  steps.indexOf(currentStep) < index ? "secondary" : "primary"
                }
                key={step}
                onClick={() =>
                  isProgressBarStepClickable(step) && setCurrentStep(step)
                }
                style={{
                  cursor: isProgressBarStepClickable(step)
                    ? "pointer"
                    : "default",
                }}
              >
                {getPhaseName(getPhase(step))}
              </Badge>
            ) : (
              <span
                key={step}
                style={{
                  height: "7px",
                  width: "7px",
                  backgroundColor:
                    steps.indexOf(currentStep) < index
                      ? "var(--bs-secondary)"
                      : "var(--bs-primary)",
                  borderRadius: "50%",
                  cursor: isProgressBarStepClickable(step)
                    ? "pointer"
                    : "default",
                }}
                onClick={() =>
                  isProgressBarStepClickable(step) && setCurrentStep(step)
                }
              />
            ),
          )}
        </small>
        <ProgressBar
          id={"footer_narrowscreen"}
          now={((steps.indexOf(currentStep) + 1) / steps.length) * 100}
        />
      </div>
    </div>
  );
};

export default BestellWizardMobileFooter;
