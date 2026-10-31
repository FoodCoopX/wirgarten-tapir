import React, { ReactNode, useEffect } from "react";
import "../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { PersonalData } from "../bestell_wizard/types/PersonalData.ts";
import BestellWizardMobileFooter from "../bestell_wizard_mobile/components/BestellWizardMobileFooter.tsx";
import BestellWizardMobileHeader from "../bestell_wizard_mobile/components/BestellWizardMobileHeader.tsx";
import StepBase from "../bestell_wizard_mobile/components/StepBase.tsx";
import { Step } from "../bestell_wizard_mobile/types/Step.ts";
import {
  CONTENT_HEIGHT,
  HEADER_HEIGHT,
} from "../bestell_wizard_mobile/utils/DIMENSIONS.ts";
import { getStepTopPosition } from "../bestell_wizard_mobile/utils/getStepTopPosition.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import { BiddingRoundTexts } from "./types/BiddingRoundTypes.ts";
import { getBiddingRoundStepBackground } from "./utils/getBiddingRoundStepBackground.ts";
import { getBiddingRoundStepTitle } from "./utils/getBiddingRoundStepTitle.ts";

interface BiddingRoundMobileProps {
  settings: BestellWizardSettings;
  texts: BiddingRoundTexts;
  steps: Step[];
  currentStep: Step;
  setCurrentStep: (step: Step) => void;
  personalData: PersonalData;
  getStepComponent: (step: Step) => ReactNode;
  toastDatas: ToastData[];
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  showProgress: boolean;
  hideFooterButtonsOnLastStep: boolean;
  setTestData: () => void;
}

const BiddingRoundMobile: React.FC<BiddingRoundMobileProps> = ({
  settings,
  texts,
  steps,
  currentStep,
  setCurrentStep,
  personalData,
  getStepComponent,
  toastDatas,
  setToastDatas,
  showProgress,
  hideFooterButtonsOnLastStep,
  setTestData,
}) => {
  useEffect(() => {
    const element = document.getElementById(currentStep);
    element?.scrollIntoView({ behavior: "smooth" });
  }, [currentStep, steps]);

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
      <div style={{ height: HEADER_HEIGHT + "dvh", width: "100%" }}>
        <BestellWizardMobileHeader
          settings={settings}
          showShoppingCart={false}
          shoppingCart={{}}
          phases={[]}
          selectedPickupLocations={[]}
          solidarityContribution={0}
          atLeastOneProductTypeInWaitingList={false}
          productTypesInWaitingList={new Set()}
          steps={steps}
          currentStep={currentStep}
          selectedNumberOfCoopShares={0}
          goToProductTypeStep={() => {}}
          contractStartDate={new Date()}
          selectedGrowingPeriod={undefined}
          setCurrentStep={setCurrentStep}
        />
      </div>
      <div
        style={{ height: CONTENT_HEIGHT + "dvh", width: "100%" }}
        id={"scroll_container"}
      >
        {steps.map((step) => (
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
              title={getBiddingRoundStepTitle(step, settings, texts)}
              firstName={personalData.firstName}
              active={step === currentStep}
              content={getStepComponent(step)}
              backgroundImageUrl={getBiddingRoundStepBackground(step, settings)}
            />
          </div>
        ))}
      </div>
      {currentStep !== "loading" && (
        <BestellWizardMobileFooter
          steps={steps}
          currentStep={currentStep}
          setCurrentStep={setCurrentStep}
          settings={settings}
          setTestData={setTestData}
          showProgress={showProgress}
          hideButtonsOnLastStep={hideFooterButtonsOnLastStep}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default BiddingRoundMobile;
