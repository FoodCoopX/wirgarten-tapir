import React from "react";
import { Badge, Modal, Table } from "react-bootstrap";
import "dayjs/locale/de";

import "../../fixed_header.css";
import { ExtendedPaymentsByDueDate } from "../../types/ExtendedPaymentsByDueDate.ts";
import { formatDateText } from "../../utils/formatDateText.ts";
import dayjs from "dayjs";
import RelativeTime from "dayjs/plugin/relativeTime";
import { ExtendedPayment, Payment } from "../../api-client";
import formatSubscription from "../../utils/formatSubscription.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import PlaceholderTableRows from "../../components/PlaceholderTableRows.tsx";
import { getMinimumDate } from "../../utils/getMinimumDate.ts";
import { getMaximumDate } from "../../utils/getMaximumDate.ts";

interface FuturePaymentsModalProps {
  extendedPaymentsByDueDate: ExtendedPaymentsByDueDate;
  show: boolean;
  onHide: () => void;
  loading: boolean;
}

const FuturePaymentsModal: React.FC<FuturePaymentsModalProps> = ({
  onHide,
  show,
  extendedPaymentsByDueDate,
  loading,
}) => {
  dayjs.extend(RelativeTime);

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

  function getStartDate(extendedPayment: ExtendedPayment) {
    const paymentRangeStart =
      extendedPayment.payment.subscriptionPaymentRangeStart;
    const subscriptionStartDates = extendedPayment.subscriptions.map(
      (subscription) => subscription.startDate,
    );
    const earliestSubscriptionStart = getMinimumDate(subscriptionStartDates);
    if (earliestSubscriptionStart < paymentRangeStart!) {
      return paymentRangeStart;
    }

    return earliestSubscriptionStart;
  }

  function getEndDate(extendedPayment: ExtendedPayment) {
    const paymentRangeEnd = extendedPayment.payment.subscriptionPaymentRangeEnd;
    const subscriptionEndDates = extendedPayment.subscriptions.map(
      (subscription) => subscription.endDate ?? new Date("9999-12-31"),
    );
    const latestSubscriptionEnd = getMaximumDate(subscriptionEndDates);
    if (latestSubscriptionEnd > paymentRangeEnd!) {
      return paymentRangeEnd;
    }

    return latestSubscriptionEnd;
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h4>Zahlungen</h4>
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Table striped hover responsive>
          <thead style={{ textAlign: "center" }}>
            <tr>
              <th>Datum</th>
              <th>Zahlungen</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <PlaceholderTableRows nbColumns={2} nbRows={12} size={"lg"} />
            ) : (
              Object.entries(extendedPaymentsByDueDate).map(
                ([dueDateAsString, extendedPayments]) => (
                  <tr key={dueDateAsString}>
                    <td style={{ textAlign: "center" }}>
                      <div className={"d-flex flex-column"}>
                        <strong>
                          {formatDateText(new Date(dueDateAsString))}
                        </strong>
                        <span>{dayjs().to(new Date(dueDateAsString))}</span>
                      </div>
                    </td>
                    <td>
                      <div className={"d-flex flex-column"}>
                        {extendedPayments.map((extendedPayment) => (
                          <div
                            key={
                              extendedPayment.payment.dueDate.getTime() +
                              "_" +
                              extendedPayment.payment.type
                            }
                          >
                            <div
                              className={
                                "d-flex flex-column align-items-center"
                              }
                            >
                              <strong>
                                {formatCurrency(extendedPayment.payment.amount)}
                              </strong>
                              <span>{extendedPayment.payment.mandateRef}</span>
                              {extendedPayment.subscriptions.map(
                                (subscription) => (
                                  <span key={subscription.id}>
                                    {formatSubscription(subscription)}
                                  </span>
                                ),
                              )}
                              {extendedPayment.subscriptions.length > 0 && (
                                <span>
                                  {formatDateNumeric(
                                    getStartDate(extendedPayment),
                                  )}
                                  {" -> "}
                                  {formatDateNumeric(
                                    getEndDate(extendedPayment),
                                  )}
                                </span>
                              )}
                              {extendedPayment.coopShareTransactions.map(
                                (transaction) => (
                                  <span key={transaction.id}>
                                    {transaction.quantity}
                                    {" × Genossenschaftsanteile"}
                                  </span>
                                ),
                              )}
                              <Badge
                                bg={getBadgeBackground(extendedPayment.payment)}
                              >
                                {getBadgeText(extendedPayment.payment)}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                ),
              )
            )}
          </tbody>
        </Table>
      </Modal.Body>
    </Modal>
  );
};

export default FuturePaymentsModal;
