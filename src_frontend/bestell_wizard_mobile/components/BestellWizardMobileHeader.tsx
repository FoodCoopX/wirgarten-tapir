import React, { useState } from "react";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import BestellWizardShoppingCartOverlay from "./BestellWizardShoppingCartOverlay.tsx";
import { Phase } from "../types/Phase.ts";
import { PublicPickupLocation } from "../../api-client";
import { Step } from "../types/Step.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { HEADER_HEIGHT } from "../utils/DIMENSIONS.ts";
import { getMonthlyPayment } from "../utils/getMonthlyPayment.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import "./header.css";

interface BestellWizardMobileHeaderProps {
  settings: BestellWizardSettings;
  showShoppingCart: boolean;
  shoppingCart: ShoppingCart;
  phases: Phase[];
  selectedPickupLocations: PublicPickupLocation[];
  steps: Step[];
  setCurrentStep: (step: Step) => void;
  solidarityContribution: number;
}

const BestellWizardMobileHeader: React.FC<BestellWizardMobileHeaderProps> = ({
  settings,
  showShoppingCart,
  shoppingCart,
  phases,
  selectedPickupLocations,
  steps,
  setCurrentStep,
  solidarityContribution,
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
        className={"d-flex align-items-center"}
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
              formatCurrency(
                getMonthlyPayment(
                  solidarityContribution,
                  shoppingCart,
                  settings,
                ),
              ) + " / Monat"
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
        steps={steps}
        setCurrentStep={setCurrentStep}
      />
    </>
  );
};

export default BestellWizardMobileHeader;
