import React, { useState } from "react";
import {
  AssociationMembershipType,
  PublicGrowingPeriod,
  PublicPickupLocation,
  PublicProductType,
} from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../../components/mobile_wizard/utils/BUTTON_VARIANT.ts";
import { HEADER_HEIGHT } from "../../components/mobile_wizard/utils/DIMENSIONS.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { Phase } from "../types/Phase.ts";
import { Step } from "../types/Step.ts";
import { getMonthlyPayment } from "../utils/getMonthlyPayment.ts";
import BestellWizardShoppingCartOverlay from "./BestellWizardShoppingCartOverlay.tsx";

interface BestellWizardMobileHeaderProps {
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  phases: Phase[];
  selectedPickupLocations: PublicPickupLocation[];
  solidarityContribution: number;
  atLeastOneProductTypeInWaitingList: boolean;
  productTypesInWaitingList: Set<PublicProductType>;
  steps: Step[];
  currentStep: Step;
  selectedNumberOfCoopShares: number;
  goToProductTypeStep: (productType: PublicProductType) => void;
  associationMembershipType?: AssociationMembershipType;
  contractStartDate: Date | undefined;
  selectedGrowingPeriod: PublicGrowingPeriod | undefined;
  setCurrentStep: (step: Step) => void;
}

const BestellWizardMobileHeader: React.FC<BestellWizardMobileHeaderProps> = ({
  settings,
  shoppingCart,
  phases,
  selectedPickupLocations,
  solidarityContribution,
  atLeastOneProductTypeInWaitingList,
  productTypesInWaitingList,
  steps,
  currentStep,
  selectedNumberOfCoopShares,
  goToProductTypeStep,
  associationMembershipType,
  contractStartDate,
  selectedGrowingPeriod,
  setCurrentStep,
}) => {
  const [showOverlay, setShowOverlay] = useState(false);

  return (
    <>
      <TapirButton
        variant={BUTTON_VARIANT}
        style={{
          position: "absolute",
          right: "0.5rem",
          top: HEADER_HEIGHT / 2 + "dvh",
          transform: "translate(0, -50%)",
        }}
        onClick={() => setShowOverlay(true)}
        icon={"shopping_cart"}
        text={
          <span>
            {formatCurrency(
              getMonthlyPayment(
                solidarityContribution,
                shoppingCart,
                settings,
                productTypesInWaitingList,
                associationMembershipType,
                contractStartDate,
              ),
            ) + " / Monat"}
            {atLeastOneProductTypeInWaitingList && (
              <>
                <br />
                <small>ohne Warteliste</small>
              </>
            )}
          </span>
        }
      />
      <BestellWizardShoppingCartOverlay
        shoppingCart={shoppingCart}
        settings={settings}
        showOverlay={showOverlay}
        onHide={() => setShowOverlay(false)}
        showPickupLocations={phases.includes("pickup_location")}
        selectedPickupLocations={selectedPickupLocations}
        productTypesInWaitingList={productTypesInWaitingList}
        steps={steps}
        currentStep={currentStep}
        selectedNumberOfCoopShares={selectedNumberOfCoopShares}
        solidarityContribution={solidarityContribution}
        goToProductTypeStep={goToProductTypeStep}
        associationMembershipType={associationMembershipType}
        contractStartDate={contractStartDate}
        selectedGrowingPeriod={selectedGrowingPeriod}
        setCurrentStep={setCurrentStep}
      />
    </>
  );
};

export default BestellWizardMobileHeader;
