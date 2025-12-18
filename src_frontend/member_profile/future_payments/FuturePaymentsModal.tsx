import React from "react";
import { Badge, Form, Modal, Table } from "react-bootstrap";
import "dayjs/locale/de";

import "../../fixed_header.css";
import { formatDateText } from "../../utils/formatDateText.ts";
import dayjs from "dayjs";
import RelativeTime from "dayjs/plugin/relativeTime";
import { ExtendedPayment, MemberCredit, Payment } from "../../api-client";
import formatSubscription from "../../utils/formatSubscription.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import PlaceholderTableRows from "../../components/PlaceholderTableRows.tsx";
import { getMinimumDate } from "../../utils/getMinimumDate.ts";
import { getMaximumDate } from "../../utils/getMaximumDate.ts";
import { TransactionsByDueDate } from "../../types/TransactionsByDueDate.ts";

interface FuturePaymentsModalProps {
  transactionsByDueDate: TransactionsByDueDate;
  show: boolean;
  onHide: () => void;
  loading: boolean;
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

function getStartDate(extendedPayment: ExtendedPayment) {
  const paymentRangeStart =
    extendedPayment.payment.subscriptionPaymentRangeStart;

  const subscriptionStartDates = extendedPayment.subscriptions.map(
    (subscription) => subscription.startDate,
  );

  const contributionsStartDates = extendedPayment.solidarityContributions.map(
    (contribution) => contribution.startDate,
  );

  const minDate = getMinimumDate([
    paymentRangeStart!,
    ...subscriptionStartDates,
    ...contributionsStartDates,
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

  const maxDate = getMaximumDate([
    paymentRangeEnd!,
    ...subscriptionEndDates,
    ...contributionEndDates,
  ]);

  return getMinimumDate([maxDate, paymentRangeEnd!]);
}

const FuturePaymentsModal: React.FC<FuturePaymentsModalProps> = ({
  onHide,
  show,
  transactionsByDueDate,
  loading,
}) => {
  dayjs.extend(RelativeTime);

  function buildExtendedPayment(extendedPayment: ExtendedPayment) {
    return (
      <div
        key={
          extendedPayment.payment.dueDate.getTime() +
          "_" +
          extendedPayment.payment.type
        }
      >
        <div className={"d-flex flex-column align-items-center"}>
          <strong>{formatCurrency(extendedPayment.payment.amount)}</strong>
          <span>{extendedPayment.payment.mandateRef}</span>
          {extendedPayment.subscriptions.map((subscription) => (
            <span key={subscription.id}>
              {formatSubscription(subscription)}
            </span>
          ))}
          {extendedPayment.coopShareTransactions.map((transaction) => (
            <span key={transaction.id}>
              {transaction.quantity}
              {" × Genossenschaftsanteile"}
            </span>
          ))}
          {extendedPayment.solidarityContributions.length > 0 && (
            <span>Solidarbeitrag</span>
          )}
          {(extendedPayment.subscriptions.length > 0 ||
            extendedPayment.solidarityContributions.length > 0) && (
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
  }

  function buildCredit(credit: MemberCredit) {
    return (
      <div key={credit.id}>
        <div className={"d-flex flex-column align-items-center"}>
          <strong>{formatCurrency(credit.amount)}</strong>
          <Badge bg={"success"}>Gutschrift</Badge>
        </div>
      </div>
    );
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h4>Zahlungen</h4>
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form.Text>
          Es werden vorerst nur die vorhergesehenen Zahlungen für die nächsten
          12 Monate angezeigt
        </Form.Text>
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
              Object.entries(transactionsByDueDate).map(
                ([dueDateAsString, objects]) => (
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
                        {objects.map((object) =>
                          "payment" in object
                            ? buildExtendedPayment(object)
                            : buildCredit(object),
                        )}
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
