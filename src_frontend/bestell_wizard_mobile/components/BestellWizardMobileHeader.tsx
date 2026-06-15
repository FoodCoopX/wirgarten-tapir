import React, { useState } from "react";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { Phase } from "../types/Phase.ts";
import { Step } from "../types/Step.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { HEADER_HEIGHT } from "../utils/DIMENSIONS.ts";
import { getMonthlyPayment } from "../utils/getMonthlyPayment.ts";
import BestellWizardShoppingCartOverlay from "./BestellWizardShoppingCartOverlay.tsx";
import "./header.css";

interface BestellWizardMobileHeaderProps {
  settings: BestellWizardSettings;
  showShoppingCart: boolean;
  shoppingCart: ShoppingCart;
  phases: Phase[];
  selectedPickupLocations: PublicPickupLocation[];
  solidarityContribution: number;
  atLeastOneProductTypeInWaitingList: boolean;
  productTypesInWaitingList: Set<PublicProductType>;
  steps: Step[];
  currentStep: Step;
  setCurrentStep: (step: Step) => void;
  selectedNumberOfCoopShares: number;
  goToProductTypeStep: (productType: PublicProductType) => void;
}

const BestellWizardMobileHeader: React.FC<BestellWizardMobileHeaderProps> = ({
  settings,
  showShoppingCart,
  shoppingCart,
  phases,
  selectedPickupLocations,
  solidarityContribution,
  atLeastOneProductTypeInWaitingList,
  productTypesInWaitingList,
  steps,
  setCurrentStep,
  currentStep,
  selectedNumberOfCoopShares,
  goToProductTypeStep,
}) => {
  const [showOverlay, setShowOverlay] = useState(false);

  return (
    <>
      <div
        id={"bw-header"}
        style={{
          width: "100%",
          height: "100%",
        }}
        className={
          "d-flex align-items-center " +
          (showShoppingCart ? "" : "bw-logo-centered")
        }
      >
        {settings.logoUrl && (
          <img src={settings.logoUrl} alt={"Logo"} style={{ height: "70%" }} />
        )}
        {showShoppingCart ? (
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
        ) : (
          <div />
        )}
      </div>
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
        setCurrentStep={setCurrentStep}
        selectedNumberOfCoopShares={selectedNumberOfCoopShares}
        solidarityContribution={solidarityContribution}
        goToProductTypeStep={goToProductTypeStep}
      />
    </>
  );
};

export default BestellWizardMobileHeader;
