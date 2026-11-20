import React, { ReactNode } from "react";
import {
  AssociationMembershipType,
  PublicGrowingPeriod,
  PublicPickupLocation,
  PublicProductType,
} from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import MobileWizardBase from "../../components/mobile_wizard/MobileWizardBase.tsx";
import { ToastData } from "../../types/ToastData.ts";
import { Phase } from "../types/Phase.ts";
import { Step } from "../types/Step.ts";
import { getPhase } from "../utils/getPhase.ts";
import { getStepBackground } from "../utils/getStepBackground.ts";
import { getPhaseLabel, getStepName } from "../utils/getStepLabels.ts";
import { getStepTitle } from "../utils/getStepTitle.ts";
import BestellWizardMobileHeader from "./BestellWizardMobileHeader.tsx";

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
  associationMembershipType?: AssociationMembershipType;
  contractStartDate: Date | undefined;
  selectedGrowingPeriod: PublicGrowingPeriod | undefined;
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
  associationMembershipType,
  contractStartDate,
  selectedGrowingPeriod,
}) => {
  return (
    <MobileWizardBase
      steps={steps}
      currentStep={currentStep}
      setCurrentStep={(step) => setCurrentStep(step as Step)}
      getStepComponent={(step) => getStepComponent(step as Step)}
      getStepTitle={(step) => getStepTitle(step as Step, settings)}
      getStepBackground={(step) => getStepBackground(step as Step, settings)}
      getPhase={(step) => getPhase(step as Step)}
      getPhaseLabel={(phase) => getPhaseLabel(phase as Phase, settings)}
      getStepName={(step) => getStepName(step as Step, settings)}
      logoUrl={settings.logoUrl}
      rightHeaderContent={
        steps.indexOf(currentStep) > 2 ? (
          <BestellWizardMobileHeader
            settings={settings}
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
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            goToProductTypeStep={goToProductTypeStep}
            associationMembershipType={associationMembershipType}
            contractStartDate={contractStartDate}
            selectedGrowingPeriod={selectedGrowingPeriod}
            setCurrentStep={setCurrentStep}
          />
        ) : undefined
      }
      firstName={personalData.firstName}
      showProgress={showProgress}
      hideFooterButtonsOnLastStep={hideFooterButtonsOnLastStep}
      showFooter={currentStep !== "loading"}
      showTestMenu={settings.debug}
      onTestData={setTestData}
      toastDatas={toastDatas}
      setToastDatas={setToastDatas}
    />
  );
};

export default BestellWizardMobileBase;
