import React, { ReactNode } from "react";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import { Phase } from "../types/Phase.ts";
import { Step } from "../types/Step.ts";
import { CONTENT_HEIGHT, HEADER_HEIGHT } from "../utils/DIMENSIONS.ts";
import { getStepBackground } from "../utils/getStepBackground.ts";
import { getStepTitle } from "../utils/getStepTitle.ts";
import { getStepTopPosition } from "../utils/getStepTopPosition.ts";
import BestellWizardMobileFooter from "./BestellWizardMobileFooter.tsx";
import BestellWizardMobileHeader from "./BestellWizardMobileHeader.tsx";
import "./footer.css";
import StepBase from "./StepBase.tsx";

interface BestellWizardMobileBaseProps {
  settings: BestellWizardSettings;
  steps: Step[];
  currentStep: Step;
  shoppingCart: ShoppingCart;
  phases: Phase[];
  selectedPickupLocations: PublicPickupLocation[];
  solidarityContribution: number;
  productTypesInWaitingList: Set<PublicProductType>;
  personalData: PersonalData;
  getStepComponent: (step: Step) => ReactNode;
  setCurrentStep: (step: Step) => void;
  setTestData: () => void;
  toastDatas: ToastData[];
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  showProgress: boolean;
  hideFooterButtonsOnLastStep: boolean;
  selectedNumberOfCoopShares: number;
  goToProductTypeStep: (productType: PublicProductType) => void;
}

const BestellWizardMobileBase: React.FC<BestellWizardMobileBaseProps> = ({
  settings,
  steps,
  currentStep,
  shoppingCart,
  phases,
  selectedPickupLocations,
  solidarityContribution,
  productTypesInWaitingList,
  personalData,
  getStepComponent,
  setCurrentStep,
  setTestData,
  toastDatas,
  setToastDatas,
  showProgress,
  hideFooterButtonsOnLastStep,
  selectedNumberOfCoopShares,
  goToProductTypeStep,
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
        <BestellWizardMobileHeader
          settings={settings}
          showShoppingCart={steps.indexOf(currentStep) > 2}
          shoppingCart={shoppingCart}
          phases={phases}
          selectedPickupLocations={selectedPickupLocations}
          solidarityContribution={solidarityContribution}
          atLeastOneProductTypeInWaitingList={
            productTypesInWaitingList.size > 0
          }
          productTypesInWaitingList={productTypesInWaitingList}
          steps={steps}
          currentStep={currentStep}
          setCurrentStep={setCurrentStep}
          selectedNumberOfCoopShares={selectedNumberOfCoopShares}
          goToProductTypeStep={goToProductTypeStep}
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

export default BestellWizardMobileBase;
