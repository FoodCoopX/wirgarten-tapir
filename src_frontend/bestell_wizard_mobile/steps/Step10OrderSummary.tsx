import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Accordion, AccordionBody } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { scrollIntoView } from "../utils/scrollIntoView.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import formatAddress from "../../utils/formatAddress.ts";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import { getProductByIdGlobal } from "../utils/getProductByIdGlobal.ts";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";

interface Step10OrderSummaryProps {
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  numberOfCoopShares: number;
  studentStatusEnabled: boolean;
  goToNextStep: () => void;
  contractStartDate: Date;
  firstDeliveryDatesByPickupLocationAndProductType: {
    [key: string]: { [key: string]: Date };
  };
  goToProductTypeStep: (pt: PublicProductType) => void;
  active: boolean;
  selectedPickupLocations: PublicPickupLocation[];
  solidarityContribution: number;
  personalData: PersonalData;
}

const Step10OrderSummary: React.FC<Step10OrderSummaryProps> = ({
  settings,
  shoppingCart,
  numberOfCoopShares,
  studentStatusEnabled,
  goToNextStep,
  contractStartDate,
  firstDeliveryDatesByPickupLocationAndProductType,
  goToProductTypeStep,
  selectedPickupLocations,
  solidarityContribution,
  personalData,
}) => {
  function getProductById(productType: PublicProductType, productId: string) {
    return productType.products.find((product) => product.id === productId);
  }

  function getTotalPriceForProductType(productType: PublicProductType) {
    let sum = 0;
    for (const [productId, quantity] of Object.entries(shoppingCart)) {
      const product = getProductById(productType, productId);
      if (!product) {
        continue;
      }
      sum += product.price * quantity;
    }
    return sum;
  }

  function getProductTypeTitle(productType: PublicProductType) {
    if (isProductTypeOrdered(productType, shoppingCart)) {
      return (
        productType.name +
        " " +
        formatCurrency(getTotalPriceForProductType(productType)) +
        " / Monat"
      );
    }

    return productType.name + " (nicht bestellt)";
  }

  function getCoopSharesTitle() {
    if (studentStatusEnabled) {
      return "Keine Mitgliedschaft in der Genossenschaft (student)";
    }

    return (
      "Mitgliedschaft in der Genossenschaft (" +
      formatCurrency(numberOfCoopShares * settings.priceOfAShare) +
      ")"
    );
  }

  function getPaymentsTitle() {
    let monthlyPayment = solidarityContribution;
    for (const [productId, quantity] of Object.entries(shoppingCart)) {
      for (const productType of settings.productTypes) {
        const product = getProductById(productType, productId);
        if (!product) {
          continue;
        }
        monthlyPayment += product.price * quantity;
      }
    }
    return "Zahlungen: " + formatCurrency(monthlyPayment) + " / Monat";
  }

  function buildProductDetails(
    productId: string,
    quantity: number,
    productType: PublicProductType,
  ) {
    const product = getProductById(productType, productId);
    if (!product) {
      return;
    }

    return (
      <li key={productId}>
        {product.name}
        {" × "}
        {quantity}: {formatCurrency(product.price * quantity)} / Monat
      </li>
    );
  }

  function getFirstDelivery(pickupLocationId: string, productTypeId: string) {
    if (
      !(pickupLocationId in firstDeliveryDatesByPickupLocationAndProductType)
    ) {
      return "";
    }

    if (
      !(
        productTypeId in
        firstDeliveryDatesByPickupLocationAndProductType[pickupLocationId]
      )
    ) {
      return "";
    }

    return formatDateNumeric(
      firstDeliveryDatesByPickupLocationAndProductType[pickupLocationId][
        productTypeId
      ],
    );
  }

  function getPaymentRhythmDisplay(givenRhythm: string) {
    for (const [rhythm, display] of Object.entries(
      settings.paymentRhythmChoices,
    )) {
      if (rhythm === givenRhythm) {
        if (rhythm === "monthly") {
          return display.slice(0, display.indexOf("("));
        }
        return display;
      }
    }

    return "Unbekannt";
  }

  return (
    <>
      <div>
        <div className={"d-flex flex-column gap-2"}>
          {settings.productTypes.map((productType) => (
            <Accordion key={productType.id}>
              <Accordion.Item
                eventKey={productType.id!.toString()}
                onClick={scrollIntoView}
              >
                <Accordion.Header>
                  {getProductTypeTitle(productType)}
                </Accordion.Header>

                <AccordionBody>
                  {isProductTypeOrdered(productType, shoppingCart) && (
                    <ul>
                      {Object.entries(shoppingCart)
                        .filter(
                          ([productId, quantity]) =>
                            doesProductBelongsToProductType(
                              productId,
                              productType,
                            ) && quantity > 0,
                        )
                        .map(([productId, quantity]) =>
                          buildProductDetails(productId, quantity, productType),
                        )}
                      <li>
                        Vertragsstart: {formatDateNumeric(contractStartDate)}
                      </li>
                      {!productType.noDelivery && (
                        <>
                          <li>
                            Erste Lieferung:{" "}
                            {selectedPickupLocations.length > 0 &&
                              getFirstDelivery(
                                selectedPickupLocations[0].id!,
                                productType.id!,
                              )}
                          </li>
                          <li>
                            Verteilstation:{" "}
                            {selectedPickupLocations.length > 0 &&
                              selectedPickupLocations[0].name +
                                " (" +
                                formatAddress(
                                  selectedPickupLocations[0].street,
                                  selectedPickupLocations[0].street2,
                                  selectedPickupLocations[0].postcode,
                                  selectedPickupLocations[0].city,
                                ) +
                                ")"}
                          </li>
                        </>
                      )}
                    </ul>
                  )}
                  <TapirButton
                    icon={"edit"}
                    text={"Bestellung anpassen"}
                    variant={BUTTON_VARIANT}
                    size={"sm"}
                    onClick={() => goToProductTypeStep(productType)}
                  />
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          ))}
          {settings.showCoopContent && (
            <Accordion>
              <Accordion.Item eventKey={"coop_shares"} onClick={scrollIntoView}>
                <Accordion.Header>{getCoopSharesTitle()}</Accordion.Header>
                <AccordionBody>
                  {studentStatusEnabled
                    ? "Keine Anteile gezeichnet da student."
                    : numberOfCoopShares +
                      " × " +
                      formatCurrency(settings.priceOfAShare) +
                      " = " +
                      formatCurrency(
                        numberOfCoopShares * settings.priceOfAShare,
                      )}
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          )}
          {(solidarityContribution > 0 ||
            isAtLeastOneProductOrdered(shoppingCart)) && (
            <Accordion>
              <Accordion.Item eventKey={"payments"} onClick={scrollIntoView}>
                <Accordion.Header>{getPaymentsTitle()}</Accordion.Header>
                <AccordionBody>
                  <ul>
                    {Object.entries(shoppingCart)
                      .filter(([_, quantity]) => quantity > 0)
                      .map(([productId, quantity]) => (
                        <li>
                          {
                            getProductByIdGlobal(
                              productId,
                              settings.productTypes,
                            )?.name
                          }
                          :{" "}
                          {formatCurrency(
                            (getProductByIdGlobal(
                              productId,
                              settings.productTypes,
                            )?.price ?? 0) * quantity,
                          )}
                        </li>
                      ))}
                    {solidarityContribution !== 0 && (
                      <li>
                        Solidarbeitrag: {formatCurrency(solidarityContribution)}
                      </li>
                    )}
                  </ul>
                  <p>
                    Zahlungsintervall:{" "}
                    {getPaymentRhythmDisplay(personalData.paymentRhythm)}
                  </p>
                  {numberOfCoopShares > 0 &&
                    !studentStatusEnabled &&
                    settings.showCoopContent && (
                      <p>
                        Einmalig:{" "}
                        {formatCurrency(
                          numberOfCoopShares * settings.priceOfAShare,
                        )}{" "}
                        (Genossenschaftsanteile)
                      </p>
                    )}
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          )}
        </div>
      </div>
      <NextStepButton onClick={goToNextStep} />
    </>
  );
};

export default Step10OrderSummary;
