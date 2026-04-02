import React, { useEffect, useState } from "react";
import { Badge, Form, Modal, Table } from "react-bootstrap";
import "dayjs/locale/de";

import "../../fixed_header.css";
import { formatDateText } from "../../utils/formatDateText.ts";
import dayjs from "dayjs";
import RelativeTime from "dayjs/plugin/relativeTime";
import {
  ExtendedPayment,
  MemberCredit,
  Payment,
  PaymentsApi,
} from "../../api-client";
import formatSubscription from "../../utils/formatSubscription.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import PlaceholderTableRows from "../../components/PlaceholderTableRows.tsx";
import { getMinimumDate } from "../../utils/getMinimumDate.ts";
import { getMaximumDate } from "../../utils/getMaximumDate.ts";
import { TransactionsByDueDate } from "../../types/TransactionsByDueDate.ts";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ToastData } from "../../types/ToastData.ts";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";

interface FuturePaymentsModalProps {
  transactionsByDueDate: TransactionsByDueDate;
  show: boolean;
  onHide: () => void;
  loading: boolean;
  csrfToken: string;
  memberId: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  trialPeriodEnabled: boolean;
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
    ...subscriptionEndDates,
    ...contributionEndDates,
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

const EXPLANATION_TEXT = (
  <div>
    <p>
      Die Zahlungsreihe zeigt dir an, wie sich der Betrag zusammensetzt, der von
      deinem Konto abgebucht wird.
    </p>
    <p>
      Sofern im Monat eine Abholung / Lieferung noch in eine ggf. vorhandene
      Probezeit fällt, wird dieser Monat nachträglich, d.h. im nächsten Monat
      bezahlt (z.B. am 5. Mai für April).
    </p>
    <p>
      Erst sobald alle Abholungen / Lieferungen eines Monats außerhalb der
      Probezeit liegen, wird der Monat vorschüssig, d.h. im Monat selbst für den
      laufenden Monat bezahlt (z.B. am 5. April für April).
    </p>
    <p>
      Im Übergang zahlst du daher in einem Monat einmal nachträglich für den
      bereits abgelaufenen Monat und einmal vorschüssig für den nächsten Monat.
    </p>
    <p>
      In Monaten in denen du aufgrund deines Vertragsstartes nicht alle
      Abholungen / Lieferungen mitmachen kannst, wird dein monatlicher Betrag
      auf Basis des Kistenpreises berechnet ((Monatspreis / 52 Wochen) und mit
      der Anzahl der wahrgenommenen Lieferungen multipliziert.
    </p>
    <p>
      Ein ggf. ausgewählter Solidarpreis wird taggenau auf den Monat
      hochgerechnet.
    </p>
    <p>
      In der Zahlungsreihe werden nur die vorhergesehenen Zahlungen für die
      nächsten 12 Monate angezeigt. Sie passen sich automatisch je nach deinen
      Aktionen (z.B. Zeichnung weiterer Anteile) an.
    </p>
  </div>
);

const FuturePaymentsModal: React.FC<FuturePaymentsModalProps> = ({
  onHide,
  show,
  transactionsByDueDate,
  loading,
  csrfToken,
  memberId,
  setToastDatas,
  trialPeriodEnabled,
}) => {
  dayjs.extend(RelativeTime);
  const api = useApi(PaymentsApi, csrfToken);

  const [showPastPayments, setShowPastPayments] = useState(false);
  const [pastPayments, setPastPayments] = useState<ExtendedPayment[]>([]);

  useEffect(() => {
    if (!show) {
      return;
    }

    api
      .paymentsApiMemberPastPaymentsRetrieve({ memberId: memberId })
      .then((response) => setPastPayments(response.payments))
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Laden der vergangene Zahlungen",
          setToastDatas,
        );
      });
  }, [show]);

  function buildExtendedPayment(extendedPayment: ExtendedPayment) {
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

  function buildTableContent() {
    if (loading) {
      return <PlaceholderTableRows nbColumns={2} nbRows={12} size={"lg"} />;
    }

    if (showPastPayments) {
      return buildTableContentPastPayments();
    }

    return buildTableContentFuturePayments();
  }

  function buildTableContentPastPayments() {
    return pastPayments.map((extendedPayment) => (
      <tr key={extendedPayment.payment.id}>
        <td style={{ textAlign: "center" }}>
          <div className={"d-flex flex-column"}>
            <strong>
              {formatDateText(new Date(extendedPayment.payment.dueDate))}
            </strong>
            <span>{dayjs().to(new Date(extendedPayment.payment.dueDate))}</span>
          </div>
        </td>
        <td>
          <div className={"d-flex flex-column"}>
            {buildExtendedPayment(extendedPayment)}
          </div>
        </td>
      </tr>
    ));
  }

  function buildTableContentFuturePayments() {
    return Object.entries(transactionsByDueDate).map(
      ([dueDateAsString, objects]) => (
        <tr key={dueDateAsString}>
          <td style={{ textAlign: "center" }}>
            <div className={"d-flex flex-column"}>
              <strong>{formatDateText(new Date(dueDateAsString))}</strong>
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
    );
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <span
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
          style={{ width: "100%" }}
        >
          <Modal.Title>
            <h4>Zahlungen</h4>
          </Modal.Title>
          <span className={"d-flex flex-row align-items-center gap-2"}>
            <Form.Check
              id={"statute"}
              checked={showPastPayments}
              onChange={(event) => setShowPastPayments(event.target.checked)}
              label={"Vergangene Zahlungen anzeigen"}
            />
            <TapirHelpButton text={EXPLANATION_TEXT} width={"700px"} />
          </span>
        </span>
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
          <tbody>{buildTableContent()}</tbody>
        </Table>
      </Modal.Body>
    </Modal>
  );
};

export default FuturePaymentsModal;
