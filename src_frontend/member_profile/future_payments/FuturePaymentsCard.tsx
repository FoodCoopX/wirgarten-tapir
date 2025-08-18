import React, { useEffect, useState } from "react";
import { Payment, PaymentsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { Card, Spinner } from "react-bootstrap";
import dayjs from "dayjs";
import "dayjs/locale/de";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateText } from "../../utils/formatDateText.ts";

interface FuturePaymentsCardProps {
  memberId: string;
  csrfToken: string;
}

const FuturePaymentsCard: React.FC<FuturePaymentsCardProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(PaymentsApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [paymentsByDueDate, setPaymentsByDueDate] = useState<{
    [dueDateAsString: string]: Payment[];
  }>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);

    api
      .paymentsApiMemberFuturePaymentsList({ memberId: memberId })
      .then((response) => {
        const groupedPayments: {
          [dueDateAsString: string]: Payment[];
        } = {};
        for (const payment of response) {
          const dueDateAsAstring = dayjs(payment.dueDate).format("YYYY-MM-DD");
          if (!(dueDateAsAstring in groupedPayments)) {
            groupedPayments[dueDateAsAstring] = [];
          }
          groupedPayments[dueDateAsAstring].push(payment);
        }
        setPaymentsByDueDate(groupedPayments);
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
    const dueDates = Object.keys(paymentsByDueDate).map((dueDateAsString) =>
      new Date(dueDateAsString).getTime(),
    );
    const earliestDate = new Date(Math.min(...dueDates));
    return dayjs(earliestDate).format("YYYY-MM-DD");
  }

  function getSumOfNextPayments() {
    const nextPayments = paymentsByDueDate[getEarliestDueDateAsString()];
    return nextPayments.reduce((sum, payment) => sum + payment.amount, 0);
  }

  function getMandateRefForNextPayments() {
    const nextPayments = paymentsByDueDate[getEarliestDueDateAsString()];
    return nextPayments[0].mandateRef;
  }

  return (
    <>
      <Card className={"mb-2"}>
        <Card.Header>
          <h5 className={"mb-0"}>Nächste Zahlung (neu)</h5>
        </Card.Header>
        <Card.Body style={{ textAlign: "center" }}>
          {loading ? (
            <Spinner />
          ) : (
            <>
              <div className={"contract-tile-number"}>
                <strong>{formatCurrency(getSumOfNextPayments())}</strong>
              </div>
              <small>
                am {formatDateText(new Date(getEarliestDueDateAsString()))}
                <br />
                {getMandateRefForNextPayments()}
              </small>
            </>
          )}
        </Card.Body>
      </Card>

      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default FuturePaymentsCard;
