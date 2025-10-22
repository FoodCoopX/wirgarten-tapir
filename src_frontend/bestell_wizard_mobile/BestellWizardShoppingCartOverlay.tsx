import React from "react";
import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { ShoppingCart } from "../bestell_wizard/types/ShoppingCart.ts";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { isProductTypeOrdered } from "../bestell_wizard/utils/isProductTypeOrdered.ts";
import { doesProductBelongsToProductType } from "../bestell_wizard/utils/doesProductBelongToProductType.ts";

interface BestellWizardProps {
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  showOverlay: boolean;
  onHide: () => void;
}

const BestellWizardShoppingCartOverlay: React.FC<BestellWizardProps> = ({
  settings,
  shoppingCart,
  showOverlay,
  onHide,
}) => {
  return (
    <>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          backgroundColor: "gray",
          opacity: showOverlay ? "0.5" : 0,
          zIndex: 1000,
          transition: "0.1s",
          pointerEvents: showOverlay ? "all" : "none",
        }}
        onClick={onHide}
      />
      <div
        style={{
          height: "100vh",
          width: "300px",
          boxShadow: "inset 1px 0 0 rgba(0, 0, 0, .1)",
          backgroundColor: "rgba(var(--bs-light-rgb), 1)",
          opacity: showOverlay ? 1 : 0,
          position: "absolute",
          right: showOverlay ? 0 : "-300px",
          transition: "0.1s",
          zIndex: 1001,
          top: 0,
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div
          style={{
            position: "absolute",
            right: "1vh",
            top: "1vh",
            fontSize: "5vh",
          }}
          className={"material-icons"}
          onClick={onHide}
        >
          close
        </div>
        <ul style={{ marginTop: "7vh" }}>
          {settings.productTypes.map((productType) => (
            <>
              <li key={productType.id}>{productType.name}</li>
              <ul>
                {isProductTypeOrdered(productType, shoppingCart) ? (
                  <>
                    {Object.entries(shoppingCart)
                      .filter(
                        ([productId, quantity]) =>
                          doesProductBelongsToProductType(
                            productId,
                            productType,
                          ) && quantity > 0,
                      )
                      .map(([productId, quantity]) => (
                        <li>
                          {
                            productType.products.find(
                              (product) => product.id == productId,
                            )?.name
                          }
                          {" × "}
                          {quantity}
                        </li>
                      ))}
                  </>
                ) : (
                  <li>Nicht bestellt</li>
                )}
              </ul>
            </>
          ))}
        </ul>
      </div>
    </>
  );
};

export default BestellWizardShoppingCartOverlay;
