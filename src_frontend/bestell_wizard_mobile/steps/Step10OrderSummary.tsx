import dayjs from "dayjs";
import React from "react";
import { Accordion, AccordionBody } from "react-bootstrap";
import {
  AssociationMembershipType,
  PublicGrowingPeriod,
  PublicPickupLocation,
  PublicProductType,
  PublicWaitingListEntryDetails,
} from "../../api-client";
import { getAssociationMembershipTypeCurrentPrice } from "../../association_memberships_config/getAssociationMembershipTypeCurrentPrice.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import TapirButton from "../../components/TapirButton.tsx";
import formatAddress from "../../utils/formatAddress.ts";
import { formatCoopShareLabel } from "../../utils/formatCoopShareLabel.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { Step } from "../types/Step.ts";
import { atLeastOneMonthlyPayment } from "../utils/atLeastOneMonthlyPayment.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { doesWaitingListHaveProductType } from "../utils/doesWaitingListHaveProductType.ts";
import { getAssociationMembershipTypeMonthlyPriceFormatted } from "../utils/getAssociationMembershipTypeMonthlyPriceFormatted.ts";
import { getFirstPickupLocationWithCapacity } from "../utils/getFirstPickupLocationWithCapacity.ts";
import { getNumberOfCoopShareInstalments } from "../utils/getNumberOfCoopShareInstalments.ts";
import {
  getProductById,
  getProductByIdGlobal,
} from "../utils/getProductByIdGlobal.ts";
import { getProductTypeByProductId } from "../utils/getProductTypeByProductId.ts";
import { getTotalPriceForProductType } from "../utils/getTotalPriceForProductType.ts";
import { getVisibleAssociationMembershipTypes } from "../utils/getVisibleAssociationMembershipTypes.ts";
import { scrollIntoView } from "../utils/scrollIntoView.ts";
import { willBecomeMemberNow } from "../utils/willBecomeMemberNow.ts";

interface Step10OrderSummaryProps {
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  numberOfCoopShares: number;
  payCoopSharesInInstalments?: boolean;
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
  confirmOrder: () => void | undefined;
  confirmOrderLoading: boolean;
  isOrderStep: boolean;
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined;
  singleProductType?: PublicProductType;
  associationMembershipType?: AssociationMembershipType;
  selectedGrowingPeriod: PublicGrowingPeriod | undefined;
  hideTrialPeriod: boolean;
  stepActive: boolean;
  setCurrentStep: (step: Step) => void;
}

const PaymentRow: React.FC<{
  label: string;
  amount: number;
  perMonth?: boolean;
}> = ({ label, amount, perMonth }) => (
  <div className={"d-flex justify-content-between gap-3"}>
    <span>{label}</span>
    <span className={"text-nowrap"}>
      {formatCurrency(amount)}
      {perMonth && " / Monat"}
    </span>
  </div>
);

const Step10OrderSummary: React.FC<Step10OrderSummaryProps> = ({
  settings,
  shoppingCart,
  numberOfCoopShares,
  payCoopSharesInInstalments,
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
  confirmOrder,
  confirmOrderLoading,
  isOrderStep,
  waitingListEntryDetails,
  singleProductType,
  associationMembershipType,
  selectedGrowingPeriod,
  hideTrialPeriod,
  stepActive,
  setCurrentStep,
}) => {
  function getRelevantPickupLocation(): PublicPickupLocation | undefined {
    if (waitingListEntryDetails === undefined) {
      return getFirstPickupLocationWithCapacity(
        selectedPickupLocations,
        pickupLocationsWithCapacityFull,
      );
    }

    if (selectedPickupLocations.length > 0) {
      return selectedPickupLocations[0];
    }

    return waitingListEntryDetails.currentPickupLocation;
  }

  const activePickupLocation = getRelevantPickupLocation();

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
      return settings.strings.step10FlagStudent;
    }

    return (
      "Mitgliedschaft in der Genossenschaft (" +
      formatCurrency(numberOfCoopShares * settings.priceOfAShare) +
      ")"
    );
  }

  function getAssociationMembershipTitle() {
    if (!associationMembershipType) {
      return "Keine Vereinsmitgliedschaft";
    }

    return (
      "Vereinsmitgliedschaft: " +
      associationMembershipType.name +
      getAssociationMembershipTypeMonthlyPriceFormatted(
        associationMembershipType,
        contractStartDate,
      )
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

  function getDateOfFirstDelivery(productTypeId: string) {
    const pickupLocation = getRelevantPickupLocation();
    if (!pickupLocation) {
      return undefined;
    }
    const pickupLocationId = pickupLocation.id!;

    if (
      !(pickupLocationId in firstDeliveryDatesByPickupLocationAndProductType)
    ) {
      return undefined;
    }

    if (
      !(
        productTypeId in
        firstDeliveryDatesByPickupLocationAndProductType[pickupLocationId]
      )
    ) {
      return undefined;
    }

    return firstDeliveryDatesByPickupLocationAndProductType[pickupLocationId][
      productTypeId
    ];
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

  function getPickupLocationWishHeading() {
    if (activePickupLocation) {
      return "Weitere Verteilstation-Wünsche auf Warteliste:";
    }

    if (getLocationsNotActive().length === 1) {
      return "Verteilstation auf der Warteliste:";
    }

    return "Verteilstationen auf der Warteliste:";
  }

  function getEndOfTrialPeriod(productTypeId: string) {
    const firstDelivery = dayjs(getDateOfFirstDelivery(productTypeId));
    return firstDelivery
      .subtract(firstDelivery.get("day") - 1, "days")
      .add(settings.trialPeriodLengthInWeeks, "week")
      .subtract(1, "day")
      .toDate();
  }

  function getProductTypeList() {
    if (singleProductType) {
      return [singleProductType];
    }

    if (selectedGrowingPeriod) {
      return selectedGrowingPeriod.productTypes;
    }

    return settings.productTypes;
  }

  function isOneTimePaymentShown() {
    return (
      !singleProductType &&
      !studentStatusEnabled &&
      settings.showCoopContent &&
      !waitingListEntryDetails?.memberAlreadyExists
    );
  }

  function getMonthlyPayments() {
    const payments: { key: string; label: string; amount: number }[] =
      Object.entries(shoppingCart)
        .filter(([_, quantity]) => quantity > 0)
        .map(([productId, quantity]) => {
          const product = getProductByIdGlobal(
            productId,
            settings.productTypes,
          );
          const startsWhenSpaceFree = doesWaitingListHaveProductType(
            productTypesInWaitingList,
            getProductTypeByProductId(productId, settings)!,
          );
          return {
            key: productId,
            label:
              (product?.name ?? "") +
              (startsWhenSpaceFree ? " (Start wenn Platz frei)" : ""),
            amount: (product?.price ?? 0) * quantity,
          };
        });

    if (solidarityContribution !== 0) {
      payments.push({
        key: "solidarity_contribution",
        label: "Solidarbeitrag",
        amount: solidarityContribution,
      });
    }

    const associationMembershipPrice =
      associationMembershipType &&
      getAssociationMembershipTypeCurrentPrice(
        associationMembershipType,
        contractStartDate,
      );
    if (associationMembershipType && associationMembershipPrice) {
      payments.push({
        key: "association_membership",
        label: "Vereinsmitgliedschaft: " + associationMembershipType.name,
        amount: associationMembershipPrice.priceAsFloat,
      });
    }

    return payments;
  }

  const monthlyPayments = getMonthlyPayments();

  function getPaymentSegments() {
    const segments: React.ReactNode[] = [];

    if (isOneTimePaymentShown() && payCoopSharesInInstalments) {
      segments.push(
        <>
          <strong>
            {getNumberOfCoopShareInstalments(numberOfCoopShares, settings)}{" "}
            monatliche Raten:
          </strong>
          <PaymentRow
            label={
              "Genossenschaftsanteile" +
              (willBecomeMemberNow(settings, becomeMemberNow)
                ? ""
                : " (Start wenn Platz frei)")
            }
            amount={settings.coopShareInstalmentAmount}
            perMonth={true}
          />
        </>,
      );
    } else if (isOneTimePaymentShown()) {
      segments.push(
        <>
          <strong>Einmalig:</strong>
          <PaymentRow
            label={
              "Genossenschaftsanteile" +
              (willBecomeMemberNow(settings, becomeMemberNow)
                ? ""
                : " (Start wenn Platz frei)")
            }
            amount={numberOfCoopShares * settings.priceOfAShare}
          />
        </>,
      );
    }

    if (monthlyPayments.length > 0) {
      segments.push(
        <>
          <strong>Wiederkehrend:</strong>
          <ul className={"mb-0"}>
            {monthlyPayments.map((payment) => (
              <li key={payment.key}>
                <PaymentRow
                  label={payment.label}
                  amount={payment.amount}
                  perMonth
                />
              </li>
            ))}
          </ul>
          {atLeastOneMonthlyPayment(
            shoppingCart,
            productTypesInWaitingList,
            solidarityContribution,
          ) && (
            <>
              <hr />
              Zahlungsintervall:{" "}
              {getPaymentRhythmDisplay(personalData.paymentRhythm)}
            </>
          )}
        </>,
      );
    }

    return segments;
  }

  return (
    <>
      <div>
        <div className={"d-flex flex-column gap-2"}>
          {settings.strings.step10SingleProductTypeHint && (
            <div className={"text-center mb-2"}>
              <span
                dangerouslySetInnerHTML={{
                  __html: settings.strings.step10SingleProductTypeHint,
                }}
              ></span>
            </div>
          )}
          {getProductTypeList().map((productType) => (
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
                      {doesWaitingListHaveProductType(
                        productTypesInWaitingList,
                        productType,
                      ) ? (
                        <li>Warteliste</li>
                      ) : (
                        <>
                          <li>
                            Vertragsstart:{" "}
                            {formatDateNumeric(contractStartDate)}
                          </li>
                          {!productType.noDelivery && (
                            <>
                              <li>
                                Erste Abholung:{" "}
                                {(selectedPickupLocations.length > 0 ||
                                  waitingListEntryDetails?.currentPickupLocation) &&
                                  formatDateNumeric(
                                    getDateOfFirstDelivery(productType.id!),
                                  )}
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
                              {!hideTrialPeriod &&
                                settings.trialPeriodLengthInWeeks > 0 && (
                                  <li>
                                    Probezeit bis{" "}
                                    {formatDateNumeric(
                                      getEndOfTrialPeriod(productType.id!),
                                    )}
                                  </li>
                                )}
                            </>
                          )}
                        </>
                      )}

                      {!productType.noDelivery &&
                        getLocationsNotActive().length > 0 && (
                          <li>
                            <div>{getPickupLocationWishHeading()}</div>
                            <ul>
                              {getLocationsNotActive().map((pickupLocation) => (
                                <li key={pickupLocation.id}>
                                  {pickupLocation.name}
                                </li>
                              ))}
                            </ul>
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
          {!singleProductType &&
            settings.showCoopContent &&
            willBecomeMemberNow(settings, becomeMemberNow) &&
            !waitingListEntryDetails?.memberAlreadyExists && (
              <Accordion>
                <Accordion.Item
                  eventKey={"coop_shares"}
                  onClick={scrollIntoView}
                >
                  <Accordion.Header>{getCoopSharesTitle()}</Accordion.Header>
                  <AccordionBody>
                    {studentStatusEnabled ? (
                      settings.strings.step10TextStudent
                    ) : (
                      <>
                        {numberOfCoopShares +
                          " " +
                          formatCoopShareLabel(numberOfCoopShares) +
                          " à " +
                          formatCurrency(settings.priceOfAShare) +
                          " = " +
                          formatCurrency(
                            numberOfCoopShares * settings.priceOfAShare,
                          )}
                        {payCoopSharesInInstalments && (
                          <>
                            <br />
                            {"in " +
                              getNumberOfCoopShareInstalments(
                                numberOfCoopShares,
                                settings,
                              ) +
                              " monatlichen Raten à " +
                              formatCurrency(
                                settings.coopShareInstalmentAmount,
                              )}
                          </>
                        )}
                      </>
                    )}
                    <TapirButton
                      variant={BUTTON_VARIANT}
                      size={"sm"}
                      text={"Anteile anpassen"}
                      icon={"edit"}
                      onClick={() => {
                        setCurrentStep("6b_coop_shares");
                      }}
                    />
                  </AccordionBody>
                </Accordion.Item>
              </Accordion>
            )}
          {associationMembershipType && (
            <Accordion>
              <Accordion.Item
                eventKey={"association_membership"}
                onClick={scrollIntoView}
              >
                <Accordion.Header>
                  {getAssociationMembershipTitle()}
                </Accordion.Header>
                <AccordionBody>
                  <li>{associationMembershipType.name}</li>
                  {getAssociationMembershipTypeCurrentPrice(
                    associationMembershipType,
                    contractStartDate,
                  ) && (
                    <li>
                      {getAssociationMembershipTypeMonthlyPriceFormatted(
                        associationMembershipType,
                        contractStartDate,
                      )}
                    </li>
                  )}
                  {getVisibleAssociationMembershipTypes(
                    settings.associationMembershipTypes,
                  ).length > 1 && (
                    <li>
                      <TapirButton
                        variant={BUTTON_VARIANT}
                        size={"sm"}
                        text={"Mitgliedschaft anpassen"}
                        icon={"edit"}
                        onClick={() => {
                          setCurrentStep("6b_association_membership");
                        }}
                      />
                    </li>
                  )}
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          )}
          {solidarityContribution !== 0 && (
            <Accordion>
              <Accordion.Item
                eventKey={"solidarity_contribution"}
                onClick={scrollIntoView}
              >
                <Accordion.Header>
                  Solidarbeitrag: {formatCurrency(solidarityContribution)} /
                  Monat
                </Accordion.Header>
                <AccordionBody>
                  <ul>
                    <li>
                      Betrag: {formatCurrency(solidarityContribution)} / Monat
                    </li>
                    <li>Gültig ab: {formatDateNumeric(contractStartDate)}</li>
                  </ul>
                  {(waitingListEntryDetails === undefined ||
                    waitingListEntryDetails.shouldShowSolidarityStep) && (
                    <TapirButton
                      variant={BUTTON_VARIANT}
                      size={"sm"}
                      text={"Solidarbeitrag anpassen"}
                      icon={"edit"}
                      onClick={() => {
                        setCurrentStep("7_solidarity_contribution");
                      }}
                    />
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
                  {getPaymentSegments().map((segment, index) => (
                    <React.Fragment key={index}>
                      {index > 0 && <hr />}
                      {segment}
                    </React.Fragment>
                  ))}
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          )}
        </div>
      </div>
      <NextStepButton
        onClick={isOrderStep ? confirmOrder : goToNextStep}
        isOrderStep={isOrderStep}
        loading={confirmOrderLoading}
        stepActive={stepActive}
      />
    </>
  );
};

export default Step10OrderSummary;
