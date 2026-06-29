import React from "react";
import { Badge } from "react-bootstrap";
import { ExtendedPayment, Payment } from "../../api-client";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import formatSubscription from "../../utils/formatSubscription.ts";
import { getMaximumDate } from "../../utils/getMaximumDate.ts";
import { getMinimumDate } from "../../utils/getMinimumDate.ts";

interface PaymentProps {
  extendedPayment: ExtendedPayment;
  trialPeriodEnabled: boolean;
}

function getStartDate(extendedPayment: ExtendedPayment) {
  const paymentRangeStart =
    extendedPayment.payment.subscriptionPaymentRangeStart;

  const subscriptionStartDates = extendedPayment.subscriptions.map(
    (subscription) => subscription.startDate,
  );

  const contributionsStartDates = extendedPayment.solidarityContributions.map(
    (contribution) => contribution.startDate,
  );

  const membershipStartDates = extendedPayment.associationMemberships.map(
    (membership) => membership.startDate,
  );

  const minDate = getMinimumDate([
    ...subscriptionStartDates,
    ...contributionsStartDates,
    ...membershipStartDates,
  ]);

  return getMaximumDate([minDate, paymentRangeStart!]);
}

function getEndDate(extendedPayment: ExtendedPayment) {
  const paymentRangeEnd = extendedPayment.payment.subscriptionPaymentRangeEnd;

  const subscriptionEndDates = extendedPayment.subscriptions.map(
    (subscription) => subscription.endDate ?? new Date("9999-12-31"),
  );

  const contributionEndDates = extendedPayment.solidarityContributions.map(
    (contribution) => contribution.endDate,
  );

  const membershipEndDates = extendedPayment.associationMemberships.map(
    (membership) => membership.endDate ?? new Date("9999-12-31"),
  );

  const maxDate = getMaximumDate([
    ...subscriptionEndDates,
    ...contributionEndDates,
    ...membershipEndDates,
  ]);

  return getMinimumDate([maxDate, paymentRangeEnd!]);
}

function partialMonthText(extendedPayment: ExtendedPayment) {
  if (
    getStartDate(extendedPayment) !==
      extendedPayment.payment.subscriptionPaymentRangeStart ||
    getEndDate(extendedPayment) !==
      extendedPayment.payment.subscriptionPaymentRangeEnd
  ) {
    return " (anteilig für Monat)";
  }
  return "";
}

function trialPeriodText(
  extendedPayment: ExtendedPayment,
  trialPeriodEnabled: boolean,
) {
  if (
    !trialPeriodEnabled ||
    !extendedPayment.payment.subscriptionPaymentRangeEnd
  ) {
    return "";
  }

  if (
    extendedPayment.payment.dueDate >
    extendedPayment.payment.subscriptionPaymentRangeEnd
  ) {
    return " (Probezeit)";
  }

  return "";
}

function getBadgeBackground(payment: Payment) {
  if (payment.dueDate > new Date()) {
    return "info";
  }

  switch (payment.status) {
    case "DUE":
      return "danger";
    case "PAID":
      return "success";
    default:
      return "info";
  }
}

function getBadgeText(payment: Payment) {
  if (payment.dueDate > new Date()) {
    return "UPCOMING";
  }

  return payment.status;
}

const PaymentComponent: React.FC<PaymentProps> = ({
  extendedPayment,
  trialPeriodEnabled,
}) => {
  return (
    <div key={extendedPayment.payment.id}>
      <div className={"d-flex flex-column align-items-center"}>
        <strong>{formatCurrency(extendedPayment.payment.amount)}</strong>
        <span>{extendedPayment.payment.mandateRef}</span>
        {extendedPayment.subscriptions.map((subscription) => (
          <span key={subscription.id}>
            {formatSubscription(subscription)}
            {partialMonthText(extendedPayment)}
            {trialPeriodText(extendedPayment, trialPeriodEnabled)}
          </span>
        ))}
        {extendedPayment.coopShareTransactions.map((transaction) => (
          <span key={transaction.id}>
            {transaction.quantity}
            {" × Genossenschaftsanteile"}
          </span>
        ))}
        {extendedPayment.solidarityContributions.length > 0 && (
          <span>
            Solidarbeitrag{partialMonthText(extendedPayment)}
            {trialPeriodText(extendedPayment, trialPeriodEnabled)}
          </span>
        )}
        {extendedPayment.associationMemberships.map((membership) => (
          <span key={membership.id}>
            Vereinsmitgliedschaft {membership.type.name}{" "}
            {extendedPayment.associationMemberships.length > 1 && (
              <span>
                {formatDateNumeric(membership.startDate)} {" -> "}{" "}
                {membership.endDate
                  ? formatDateNumeric(membership.endDate)
                  : "keine Ende"}
              </span>
            )}
          </span>
        ))}
        {(extendedPayment.subscriptions.length > 0 ||
          extendedPayment.solidarityContributions.length > 0 ||
          extendedPayment.associationMemberships.length > 0) && (
          <span>
            {formatDateNumeric(getStartDate(extendedPayment))}
            {" -> "}
            {formatDateNumeric(getEndDate(extendedPayment))}
          </span>
        )}
        <Badge bg={getBadgeBackground(extendedPayment.payment)}>
          {getBadgeText(extendedPayment.payment)}
        </Badge>
      </div>
    </div>
  );
};

export default PaymentComponent;
