import React, { useState } from "react";
import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { ShoppingCart } from "../bestell_wizard/types/ShoppingCart.ts";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import BestellWizardShoppingCartOverlay from "./BestellWizardShoppingCartOverlay.tsx";

interface BestellWizardProps {
  settings: BestellWizardSettings;
  showShoppingCart: boolean;
  shoppingCart: ShoppingCart;
}

const BestellWizardMobileHeader: React.FC<BestellWizardProps> = ({
  settings,
  showShoppingCart,
  shoppingCart,
}) => {
  const [showOverlay, setShowOverlay] = useState(false);

  return (
    <>
      <div
        style={{ width: "100%", height: "100%" }}
        className={"d-flex justify-content-center align-items-center"}
      >
        <img src={settings.logoUrl} alt={"Logo"} style={{ height: "70%" }} />
        {showShoppingCart && (
          <>
            <span
              className={"material-icons"}
              style={{
                position: "absolute",
                right: "2.5vh",
                top: "2.5vh",
                fontSize: "5vh",
              }}
              onClick={() => setShowOverlay(true)}
            >
              shopping_cart
            </span>
            <span
              style={{
                backgroundColor: "var(--bs-red)",
                borderRadius: "50%",
                width: "2.5vh",
                height: "2.5vh",
                color: "white",
                position: "absolute",
                top: "1vh",
                right: "1vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {Object.values(shoppingCart).reduce(
                (sum, quantity) => sum + quantity,
                0,
              )}
            </span>
          </>
        )}
      </div>
      <BestellWizardShoppingCartOverlay
        shoppingCart={shoppingCart}
        settings={settings}
        showOverlay={showOverlay}
        onHide={() => setShowOverlay(false)}
      />
    </>
  );
};

export default BestellWizardMobileHeader;
