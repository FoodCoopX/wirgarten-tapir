import React, { useEffect, useState } from "react";
import { Modal, Table } from "react-bootstrap";
import {
  Member,
  Payment,
  PaymentsApi,
  PaymentTransaction,
} from "../api-client";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateMonthAndYear } from "../utils/formatDateMonthAndYear.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface PaymentTransactionsDetailsModalProps {
  transaction: PaymentTransaction;
  onHide: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

function formatPaymentType(type: string) {
  if (type === "payment_type_solidarity_contribution") {
    return "Solidarbeitrag";
  }
  return type;
}

const PaymentTransactionsDetailsModal: React.FC<
  PaymentTransactionsDetailsModalProps
> = ({ transaction, onHide, setToastDatas }) => {
  const api = useApi(PaymentsApi, "unused");
  const [loading, setLoading] = useState(true);
  const [membersByMandateRef, setMembersByMandateRef] = useState<
    Record<string, Member>
  >({});
  const [paymentsByMandateRef, setPaymentsByMandateRef] = useState<
    Record<string, Payment[]>
  >({});
  const [intendedUseByMandateRef, setIntendedUseByMandateRef] = useState<
    Record<string, string>
  >({});

  useEffect(() => {
    api
      .paymentsApiPaymentTransactionDetailsRetrieve({
        transactionId: transaction.id!,
      })
      .then((response) => {
        setMembersByMandateRef(response.membersByMandateRef);
        setIntendedUseByMandateRef(response.intendedUseByMandateRef);
        setPaymentsByMandateRef(
          Object.fromEntries(
            Object.entries(response.paymentsByMandateRef).map(
              ([mandateRef, paymentsObject]) => [
                mandateRef,
                paymentsObject.payments,
              ],
            ),
          ),
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Lastschrift-Details",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [transaction]);

  function getSortedMandateRefs() {
    return Object.keys(membersByMandateRef).toSorted(
      (refA: string, refB: string) => {
        const memberA = membersByMandateRef[refA];
        const memberB = membersByMandateRef[refB];

        if (memberA.memberNo && memberB.memberNo) {
          return memberA.memberNo - memberB.memberNo;
        }

        if (memberA.memberNo) {
          return -1;
        }

        if (memberB.memberNo) {
          return 1;
        }

        return memberA.lastName.localeCompare(memberB.lastName);
      },
    );
  }

  function getPaymentRangeDetails(payment: Payment) {
    if (!payment.subscriptionPaymentRangeStart) {
      return;
    }

    return (
      <span>
        , {formatDateNumeric(payment.subscriptionPaymentRangeStart)} -{" "}
        {formatDateNumeric(payment.subscriptionPaymentRangeEnd)}
      </span>
    );
  }

  function buildLine(mandateRef: string) {
    const member = membersByMandateRef[mandateRef];
    const payments = paymentsByMandateRef[mandateRef];
    const sum = payments.reduce((sum, payment) => payment.amount + sum, 0);

    return (
      <tr key={mandateRef}>
        <td>
          {member.memberNo && <span>#{member.memberNo}</span>} {member.lastName}{" "}
          {member.firstName}
        </td>
        <td>{mandateRef}</td>
        <td>{intendedUseByMandateRef[mandateRef]}</td>
        <td>{formatCurrency(sum)}</td>
        <td>
          <ul>
            {payments.map((payment) => (
              <li key={payment.id}>
                {formatPaymentType(payment.type)}{" "}
                {formatCurrency(payment.amount)}
                {getPaymentRangeDetails(payment)}
              </li>
            ))}
          </ul>
        </td>
      </tr>
    );
  }

  return (
    <Modal show={true} onHide={onHide} centered={true} size={"xl"}>
      <Modal.Header closeButton>
        <Modal.Title>
          Lastschrift Details: {transaction.type}{" "}
          {formatDateMonthAndYear(transaction.month)}{" "}
          {formatCurrency(transaction.paymentsSum)}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Table responsive hover striped bordered>
          <thead>
            <tr>
              <th>Mitglied</th>
              <th>Mandatsreferenz</th>
              <th>Verwendungszweck</th>
              <th>Summe</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <PlaceholderTableRows nbRows={100} nbColumns={4} size={"lg"} />
            ) : (
              getSortedMandateRefs().map(buildLine)
            )}
          </tbody>
        </Table>
      </Modal.Body>
    </Modal>
  );
};

export default PaymentTransactionsDetailsModal;
