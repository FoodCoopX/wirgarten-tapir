import React from "react";
import { Badge, Dropdown, DropdownButton, ProgressBar } from "react-bootstrap";
import TapirButton from "../TapirButton.tsx";
import "./footer.css";
import { MobileWizardPhase, MobileWizardStep } from "./types/MobileWizard.ts";
import { BUTTON_VARIANT } from "./utils/BUTTON_VARIANT.ts";
import { FOOTER_HEIGHT } from "./utils/DIMENSIONS.ts";

interface MobileWizardFooterProps {
  steps: MobileWizardStep[];
  currentStep: MobileWizardStep;
  setCurrentStep: (step: MobileWizardStep) => void;
  getPhase: (step: MobileWizardStep) => MobileWizardPhase;
  getPhaseLabel: (phase: MobileWizardPhase) => string;
  getStepName: (step: MobileWizardStep) => string;
  showProgress: boolean;
  hideButtonsOnLastStep: boolean;
  showTestMenu?: boolean;
  onTestData?: () => void;
}

const MobileWizardFooter: React.FC<MobileWizardFooterProps> = ({
  steps,
  currentStep,
  setCurrentStep,
  getPhase,
  getPhaseLabel,
  getStepName,
  showProgress,
  hideButtonsOnLastStep,
  showTestMenu,
  onTestData,
}) => {
  function goToPreviousStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex - 1 < 0) {
      return;
    }

    setCurrentStep(steps[steps.indexOf(currentStep) - 1]);
  }

  function isStepFirstInPhase(step: MobileWizardStep, index: number) {
    const stepPhase = getPhase(step);
    for (let i = 0; i < index; i++) {
      if (getPhase(steps[i]) == stepPhase) {
        return false;
      }
    }
    return true;
  }

  function isProgressBarStepClickable(step: MobileWizardStep) {
    return steps.indexOf(step) < steps.indexOf(currentStep);
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
        {(!hideButtonsOnLastStep || currentStep !== steps.at(-1)) && (
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
            {showTestMenu && onTestData && (
              <DropdownButton
                title={
                  <span>
                    <span
                      style={{ fontSize: "16px" }}
                      className={"material-icons"}
                    >
                      construction
                    </span>
                    <span>Test</span>
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
                <Dropdown.Item onClick={onTestData}>
                  Test daten setzen
                </Dropdown.Item>
              </DropdownButton>
            )}
          </div>
        )}
        {showProgress && (
          <>
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
                      steps.indexOf(currentStep) < index
                        ? "secondary"
                        : "primary"
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
                    {getPhaseLabel(getPhase(step))}
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
                  />
                ),
              )}
            </small>
            <ProgressBar
              id={"footer_narrowscreen"}
              now={((steps.indexOf(currentStep) + 1) / steps.length) * 100}
            />
          </>
        )}
      </div>
    </div>
  );
};

export default MobileWizardFooter;
