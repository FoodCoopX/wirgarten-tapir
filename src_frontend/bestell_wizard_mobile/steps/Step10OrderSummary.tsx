import React, { useEffect, useState } from "react";
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
import {
  getProductById,
  getProductByIdGlobal,
} from "../utils/getProductByIdGlobal.ts";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { getTotalPriceForProductType } from "../utils/getTotalPriceForProductType.ts";
import { atLeastOneMonthlyPayment } from "../utils/atLeastOneMonthlyPayment.ts";
import { getProductTypeByProductId } from "../utils/getProductTypeByProductId.ts";
import { getFirstPickupLocationWithCapacity } from "../utils/getFirstPickupLocationWithCapacity.ts";
import dayjs from "dayjs";

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
  selectedPickupLocations: PublicPickupLocation[];
  solidarityContribution: number;
  personalData: PersonalData;
  productTypesInWaitingList: Set<PublicProductType>;
  becomeMemberNow: boolean | null;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
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
  productTypesInWaitingList,
  becomeMemberNow,
  pickupLocationsWithCapacityFull,
}) => {
  const [activePickupLocation, setActivePickupLocation] =
    useState<PublicPickupLocation>();

  useEffect(() => {
    setActivePickupLocation(
      getFirstPickupLocationWithCapacity(
        selectedPickupLocations,
        pickupLocationsWithCapacityFull,
      ),
    );
  }, [selectedPickupLocations]);

  function getProductTypeTitle(productType: PublicProductType) {
    if (isProductTypeOrdered(productType, shoppingCart)) {
      return (
        productType.name +
        " " +
        formatCurrency(getTotalPriceForProductType(productType, shoppingCart)) +
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

  function getFirstDelivery(productTypeId: string) {
    const pickupLocation = getFirstPickupLocationWithCapacity(
      selectedPickupLocations,
      pickupLocationsWithCapacityFull,
    );
    if (!pickupLocation) {
      return "";
    }
    const pickupLocationId = pickupLocation.id!;

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
        return display;
      }
    }

    return "Unbekannt";
  }

  function getLocationsNotActive() {
    return selectedPickupLocations.filter(
      (pickupLocation) => pickupLocation !== activePickupLocation,
    );
  }

  function getEndOfTrialPeriod() {
    return dayjs(contractStartDate)
      .add(settings.trialPeriodLengthInWeeks, "week")
      .subtract(1, "day")
      .toDate();
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
                      {!productTypesInWaitingList.has(productType) && (
                        <li>
                          Vertragsstart: {formatDateNumeric(contractStartDate)}
                        </li>
                      )}
                      {!productType.noDelivery &&
                        !productTypesInWaitingList.has(productType) && (
                          <>
                            <li>
                              Erste Lieferung:{" "}
                              {selectedPickupLocations.length > 0 &&
                                getFirstDelivery(productType.id!)}
                            </li>
                            <li>
                              Aktive Verteilstation:{" "}
                              {activePickupLocation &&
                                activePickupLocation.name +
                                  " (" +
                                  formatAddress(
                                    activePickupLocation.street,
                                    activePickupLocation.street2,
                                    activePickupLocation.postcode,
                                    activePickupLocation.city,
                                  ) +
                                  ")"}
                            </li>
                          </>
                        )}
                      {!productType.noDelivery &&
                        getLocationsNotActive().length > 0 && (
                          <li>
                            <div>
                              Weitere Verteilstation-Wünsche auf Warteliste:
                            </div>
                            <ul>
                              {getLocationsNotActive().map((pickupLocation) => (
                                <li key={pickupLocation.id}>
                                  {pickupLocation.name}
                                </li>
                              ))}
                            </ul>
                          </li>
                        )}
                      {productTypesInWaitingList.has(productType) && (
                        <li>Warteliste</li>
                      )}
                      {!productTypesInWaitingList.has(productType) &&
                        settings.trialPeriodLengthInWeeks > 0 && (
                          <li>
                            Probezeit bis{" "}
                            {formatDateNumeric(getEndOfTrialPeriod())}
                          </li>
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
          {settings.showCoopContent && becomeMemberNow !== false && (
            <Accordion>
              <Accordion.Item eventKey={"coop_shares"} onClick={scrollIntoView}>
                <Accordion.Header>{getCoopSharesTitle()}</Accordion.Header>
                <AccordionBody>
                  {studentStatusEnabled
                    ? "Keine Anteile gezeichnet da student."
                    : numberOfCoopShares +
                      " Genossenschaftsanteile à " +
                      formatCurrency(settings.priceOfAShare) +
                      " = " +
                      formatCurrency(
                        numberOfCoopShares * settings.priceOfAShare,
                      )}
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          )}
          <hr />
          {(solidarityContribution > 0 ||
            isAtLeastOneProductOrdered(shoppingCart)) && (
            <Accordion>
              <Accordion.Item eventKey={"payments"} onClick={scrollIntoView}>
                <Accordion.Header>Deine Zahlungen</Accordion.Header>
                <AccordionBody>
                  <ul>
                    {Object.entries(shoppingCart)
                      .filter(([_, quantity]) => quantity > 0)
                      .map(([productId, quantity]) => (
                        <li key={productId}>
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
                          )}{" "}
                          / Monat
                          {productTypesInWaitingList.has(
                            getProductTypeByProductId(productId, settings)!,
                          )
                            ? " (Start wenn Platz frei)"
                            : ""}
                        </li>
                      ))}
                    {solidarityContribution !== 0 && (
                      <li>
                        Solidarbeitrag: {formatCurrency(solidarityContribution)}{" "}
                        / Monat
                      </li>
                    )}
                  </ul>
                  {atLeastOneMonthlyPayment(
                    shoppingCart,
                    productTypesInWaitingList,
                    solidarityContribution,
                  ) && (
                    <p>
                      Zahlungsintervall:{" "}
                      {getPaymentRhythmDisplay(personalData.paymentRhythm)}
                    </p>
                  )}
                  {!studentStatusEnabled && settings.showCoopContent && (
                    <p>
                      Einmalig:{" "}
                      {formatCurrency(
                        numberOfCoopShares * settings.priceOfAShare,
                      )}{" "}
                      (Genossenschaftsanteile){" "}
                      {becomeMemberNow === false && "(Start wenn Platz frei)"}
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
