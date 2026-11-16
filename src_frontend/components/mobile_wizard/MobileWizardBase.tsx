import React, { ReactNode } from "react";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { ToastData } from "../../types/ToastData.ts";
import TapirToastContainer from "../TapirToastContainer.tsx";
import MobileWizardFooter from "./MobileWizardFooter.tsx";
import MobileWizardHeader from "./MobileWizardHeader.tsx";
import StepBase from "./StepBase.tsx";
import { MobileWizardPhase, MobileWizardStep } from "./types/MobileWizard.ts";
import { CONTENT_HEIGHT, HEADER_HEIGHT } from "./utils/DIMENSIONS.ts";
import { getStepTopPosition } from "./utils/getStepTopPosition.ts";

interface MobileWizardBaseProps {
  steps: MobileWizardStep[];
  currentStep: MobileWizardStep;
  setCurrentStep: (step: MobileWizardStep) => void;
  getStepComponent: (step: MobileWizardStep) => ReactNode;
  getStepTitle: (step: MobileWizardStep) => string | undefined;
  getStepBackground: (step: MobileWizardStep) => string | undefined;
  getPhase: (step: MobileWizardStep) => MobileWizardPhase;
  getPhaseLabel: (phase: MobileWizardPhase) => string;
  getStepName: (step: MobileWizardStep) => string;
  logoUrl?: string;
  rightHeaderContent?: ReactNode;
  firstName: string;
  showProgress: boolean;
  hideFooterButtonsOnLastStep: boolean;
  showFooter?: boolean;
  showTestMenu?: boolean;
  onTestData?: () => void;
  toastDatas: ToastData[];
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const MobileWizardBase: React.FC<MobileWizardBaseProps> = ({
  steps,
  currentStep,
  setCurrentStep,
  getStepComponent,
  getStepTitle,
  getStepBackground,
  getPhase,
  getPhaseLabel,
  getStepName,
  logoUrl,
  rightHeaderContent,
  firstName,
  showProgress,
  hideFooterButtonsOnLastStep,
  showFooter = true,
  showTestMenu,
  onTestData,
  toastDatas,
  setToastDatas,
}) => {
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
        <MobileWizardHeader
          logoUrl={logoUrl}
          rightContent={rightHeaderContent}
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
                top: getStepTopPosition(step, currentStep, steps),
                width: "100%",
                pointerEvents: currentStep === step ? "auto" : "none",
              }}
            >
              <StepBase
                title={getStepTitle(step)}
                firstName={firstName}
                active={step === currentStep}
                content={getStepComponent(step)}
                backgroundImageUrl={getStepBackground(step)}
              />
            </div>
          );
        })}
      </div>
      {showFooter && (
        <MobileWizardFooter
          steps={steps}
          currentStep={currentStep}
          setCurrentStep={setCurrentStep}
          getPhase={getPhase}
          getPhaseLabel={getPhaseLabel}
          getStepName={getStepName}
          showProgress={showProgress}
          hideButtonsOnLastStep={hideFooterButtonsOnLastStep}
          showTestMenu={showTestMenu}
          onTestData={onTestData}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default MobileWizardBase;
