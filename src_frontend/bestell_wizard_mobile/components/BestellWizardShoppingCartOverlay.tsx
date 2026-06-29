import React from "react";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import {
  AssociationMembershipType,
  PublicPickupLocation,
  type PublicProductType,
} from "../../api-client";
import { getAssociationMembershipTypeCurrentPrice } from "../../association_memberships_config/getAssociationMembershipTypeCurrentPrice.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { Step } from "../types/Step.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { getAssociationMembershipTypeMonthlyPriceFormatted } from "../utils/getAssociationMembershipTypeMonthlyPriceFormatted.ts";
import { getTotalPriceForProductType } from "../utils/getTotalPriceForProductType.ts";

interface BestellWizardShoppingCartOverlayProps {
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  showOverlay: boolean;
  onHide: () => void;
  showPickupLocations: boolean;
  selectedPickupLocations: PublicPickupLocation[];
  productTypesInWaitingList: Set<PublicProductType>;
  steps: Step[];
  currentStep: Step;
  setCurrentStep: (step: Step) => void;
  selectedNumberOfCoopShares: number;
  solidarityContribution: number;
  goToProductTypeStep: (productType: PublicProductType) => void;
  associationMembershipType?: AssociationMembershipType;
}

const BestellWizardShoppingCartOverlay: React.FC<
  BestellWizardShoppingCartOverlayProps
> = ({
  settings,
  shoppingCart,
  showOverlay,
  onHide,
  showPickupLocations,
  selectedPickupLocations,
  productTypesInWaitingList,
  steps,
  currentStep,
  selectedNumberOfCoopShares,
  solidarityContribution,
  goToProductTypeStep,
  associationMembershipType,
}) => {
  function canEditProductTypeOrder(productType: PublicProductType) {
    return (
      steps.indexOf(productType.id! + "_intro") < steps.indexOf(currentStep)
    );
  }

  return (
    <>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100dvw",
          height: "100dvh",
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
          height: "100dvh",
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
            <li
              key={productType.id}
              className={
                productTypesInWaitingList.has(productType)
                  ? "text-secondary"
                  : ""
              }
            >
              <span>
                {productType.name}
                {productTypesInWaitingList.has(productType) && " (Warteliste)"}
              </span>
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
                        <li key={productId}>
                          {
                            productType.products.find(
                              (product) => product.id == productId,
                            )?.name
                          }
                          {" × "}
                          {quantity}
                        </li>
                      ))}
                    <li>
                      {formatCurrency(
                        getTotalPriceForProductType(productType, shoppingCart),
                      )}{" "}
                      pro Monat
                      {productTypesInWaitingList.has(productType) &&
                        " (erst nach einen Platz frei wird)"}
                    </li>
                  </>
                ) : (
                  <li>Nicht bestellt</li>
                )}
                {canEditProductTypeOrder(productType) && (
                  <li>
                    <TapirButton
                      variant={BUTTON_VARIANT}
                      size={"sm"}
                      text={"Bestellung anpassen"}
                      icon={"edit"}
                      onClick={() => {
                        goToProductTypeStep(productType);
                        onHide();
                      }}
                    />
                  </li>
                )}
              </ul>
            </li>
          ))}
          {associationMembershipType && (
            <li>
              Vereinsmitgliedschaft:
              <ul>
                <li>{associationMembershipType.name}</li>
                {getAssociationMembershipTypeCurrentPrice(
                  associationMembershipType,
                ) && (
                  <li>
                    {getAssociationMembershipTypeMonthlyPriceFormatted(
                      associationMembershipType,
                    )}
                  </li>
                )}
              </ul>
            </li>
          )}
          {showPickupLocations && (
            <li>
              <span>Verteilstation</span>
              {selectedPickupLocations.length === 0 ? (
                <ul>
                  <li>Nicht ausgewählt</li>
                </ul>
              ) : (
                <ol>
                  {selectedPickupLocations.map((pickupLocation) => (
                    <li key={pickupLocation.id}>{pickupLocation.name}</li>
                  ))}
                </ol>
              )}
            </li>
          )}
          {solidarityContribution !== 0 && (
            <li>
              Solidarbeitrag: {formatCurrency(solidarityContribution)} pro Monat
            </li>
          )}
          {settings.showCoopContent && selectedNumberOfCoopShares > 0 && (
            <li>
              Genossenschaftsanteile: {selectedNumberOfCoopShares} x{" "}
              {formatCurrency(settings.priceOfAShare)} ={" "}
              {formatCurrency(
                selectedNumberOfCoopShares * settings.priceOfAShare,
              )}
            </li>
          )}
        </ul>
      </div>
    </>
  );
};

export default BestellWizardShoppingCartOverlay;
