import React, { useEffect, useState } from "react";
import { ExtendedPayment, MemberCredit, PaymentsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { Card, Spinner } from "react-bootstrap";
import dayjs from "dayjs";
import "dayjs/locale/de";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateText } from "../../utils/formatDateText.ts";
import TapirButton from "../../components/TapirButton.tsx";
import FuturePaymentsModal from "./FuturePaymentsModal.tsx";
import { TransactionsByDueDate } from "../../types/TransactionsByDueDate.ts";

interface FuturePaymentsCardProps {
  memberId: string;
  csrfToken: string;
}

function sortGroupedTransactions(groupedTransactions: TransactionsByDueDate) {
  for (const key of Object.keys(groupedTransactions)) {
    groupedTransactions[key] =
      groupedTransactions[key].toSorted(compareTransactions);
  }
}

function compareTransactions(
  a: MemberCredit | ExtendedPayment,
  b: MemberCredit | ExtendedPayment,
) {
  const a_is_payment = "subscriptions" in a;
  const b_is_payment = "subscriptions" in b;
  if (a_is_payment !== b_is_payment) {
    return a_is_payment ? 1 : -1;
  }

  if (!a_is_payment || !b_is_payment) {
    return 0;
  }

  if (
    a.payment.subscriptionPaymentRangeStart &&
    b.payment.subscriptionPaymentRangeStart &&
    a.payment.subscriptionPaymentRangeStart.getTime() !==
      b.payment.subscriptionPaymentRangeStart.getTime()
  ) {
    return (
      a.payment.subscriptionPaymentRangeStart.getTime() -
      b.payment.subscriptionPaymentRangeStart.getTime()
    );
  }

  return b.payment.amount - a.payment.amount;
}

const FuturePaymentsCard: React.FC<FuturePaymentsCardProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(PaymentsApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [transactionsByDueDate, setTransactionsByDueDate] =
    useState<TransactionsByDueDate>({});
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [extendedPayments, setExtendedPayments] = useState<ExtendedPayment[]>(
    [],
  );

  useEffect(() => {
    setLoading(true);

    api
      .paymentsApiMemberFuturePaymentsRetrieve({ memberId: memberId })
      .then((response) => {
        const groupedTransactions: TransactionsByDueDate = {};

        const extendedPayments = response.payments.toSorted(
          (a, b) => a.payment.dueDate.getTime() - b.payment.dueDate.getTime(),
        );
        setExtendedPayments(extendedPayments);
        for (const extendedPayment of extendedPayments) {
          const dueDateAsAstring = dayjs(
            extendedPayment.payment.dueDate,
          ).format("YYYY-MM-DD");
          if (!(dueDateAsAstring in groupedTransactions)) {
            groupedTransactions[dueDateAsAstring] = [];
          }
          groupedTransactions[dueDateAsAstring].push(extendedPayment);
        }

        for (const memberCredit of response.credits) {
          const dueDateAsAstring = dayjs(memberCredit.dueDate).format(
            "YYYY-MM-DD",
          );
          if (!(dueDateAsAstring in groupedTransactions)) {
            groupedTransactions[dueDateAsAstring] = [];
          }
          groupedTransactions[dueDateAsAstring].push(memberCredit);
        }

        sortGroupedTransactions(groupedTransactions);

        setTransactionsByDueDate(groupedTransactions);
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Laden der Zahlungen",
          setToastDatas,
        );
      })
      .finally(() => setLoading(false));
  }, []);

  function getEarliestDueDateAsString() {
    const dueDates = extendedPayments.map((payment) =>
      payment.payment.dueDate.getTime(),
    );
    const earliestDate = new Date(Math.min(...dueDates));
    return dayjs(earliestDate).format("YYYY-MM-DD");
  }

  function getSumOfNextPayments() {
    const dueDate = getEarliestDueDateAsString();
    if (!(dueDate in transactionsByDueDate)) {
      return 0;
    }
    const nextPayments = transactionsByDueDate[getEarliestDueDateAsString()];
    return nextPayments.reduce(
      (sum, extendedPayment) => sum + getAmountIfPayment(extendedPayment),
      0,
    );
  }

  function getAmountIfPayment(object: ExtendedPayment | MemberCredit) {
    if ("payment" in object) {
      return object.payment.amount;
    }
    return 0;
  }

  function getMandateRefForNextPayments() {
    if (extendedPayments.length === 0) {
      return "Keine Mandatsreferenz";
    }
    return extendedPayments[0].payment.mandateRef;
  }

  return (
    <>
      <Card className={"mb-2"}>
        <Card.Header>
          <span
            className={
              "d-flex flex-row justify-content-between align-items-center"
            }
          >
            <h5 className={"mb-0"}>Nächste Zahlung</h5>
            <TapirButton
              variant={"outline-secondary"}
              text={"Zahlungen"}
              icon={"payment_arrow_down"}
              onClick={() => setShowModal(true)}
            />
          </span>
        </Card.Header>
        <Card.Body style={{ textAlign: "center" }}>
          {loading ? (
            <Spinner />
          ) : (
            <>
              <div className={"contract-tile-number"}>
                <strong>{formatCurrency(getSumOfNextPayments())}</strong>
              </div>
              {extendedPayments.length > 0 && (
                <small>
                  am {formatDateText(new Date(getEarliestDueDateAsString()))}
                  <br />
                  {getMandateRefForNextPayments()}
                </small>
              )}
            </>
          )}
        </Card.Body>
      </Card>
      <FuturePaymentsModal
        transactionsByDueDate={transactionsByDueDate}
        show={showModal}
        onHide={() => setShowModal(false)}
        loading={loading}
        csrfToken={csrfToken}
        memberId={memberId}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default FuturePaymentsCard;
