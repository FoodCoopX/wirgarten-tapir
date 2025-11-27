import React from "react";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { Step } from "../types/Step.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { getPhase } from "../utils/getPhase.ts";
import { Badge } from "react-bootstrap";
import { Phase } from "../types/Phase.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { FOOTER_HEIGHT } from "../utils/DIMENSIONS.ts";

interface BestellWizardMobileFooterProps {
  steps: Step[];
  currentStep: Step;
  setCurrentStep: (step: Step) => void;
  settings: BestellWizardSettings;
}

const BestellWizardMobileFooter: React.FC<BestellWizardMobileFooterProps> = ({
  steps,
  currentStep,
  setCurrentStep,
  settings,
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
            />
            <TapirButton
              size={"sm"}
              icon={"keyboard_arrow_up"}
              variant={BUTTON_VARIANT}
              onClick={goToPreviousStep}
            />
          </div>
        )}
        <small
          className={
            "d-flex flex-row flex-wrap gap-1 justify-content-center align-items-center"
          }
          style={{ width: "100%" }}
        >
          {steps.map((step, index) =>
            isStepFirstInPhase(step, index) ? (
              <Badge
                bg={
                  steps.indexOf(currentStep) < index ? "secondary" : "primary"
                }
                key={step}
                onClick={() => setCurrentStep(step)}
                style={{ cursor: "pointer" }}
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
                  cursor: "pointer",
                }}
                onClick={() => setCurrentStep(step)}
              />
            ),
          )}
        </small>
      </div>
    </div>
  );
};

export default BestellWizardMobileFooter;
