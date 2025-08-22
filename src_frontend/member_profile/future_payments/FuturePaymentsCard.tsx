import React, { useEffect, useState } from "react";
import { PaymentsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { Card, Spinner } from "react-bootstrap";
import dayjs from "dayjs";
import "dayjs/locale/de";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateText } from "../../utils/formatDateText.ts";
import { ExtendedPaymentsByDueDate } from "../../types/ExtendedPaymentsByDueDate.ts";
import TapirButton from "../../components/TapirButton.tsx";
import FuturePaymentsModal from "./FuturePaymentsModal.tsx";

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
  const [extendedPaymentsByDueDate, setExtendedPaymentsByDueDate] =
    useState<ExtendedPaymentsByDueDate>({});
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    setLoading(true);

    api
      .paymentsApiMemberFuturePaymentsList({ memberId: memberId })
      .then((response) => {
        const extendedPayments = response.sort(
          (a, b) => a.payment.dueDate.getTime() - b.payment.dueDate.getTime(),
        );
        const groupedPayments: ExtendedPaymentsByDueDate = {};
        for (const extendedPayment of extendedPayments) {
          const dueDateAsAstring = dayjs(
            extendedPayment.payment.dueDate,
          ).format("YYYY-MM-DD");
          if (!(dueDateAsAstring in groupedPayments)) {
            groupedPayments[dueDateAsAstring] = [];
          }
          groupedPayments[dueDateAsAstring].push(extendedPayment);
        }
        setExtendedPaymentsByDueDate(groupedPayments);
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
    const dueDates = Object.keys(extendedPaymentsByDueDate).map(
      (dueDateAsString) => new Date(dueDateAsString).getTime(),
    );
    const earliestDate = new Date(Math.min(...dueDates));
    return dayjs(earliestDate).format("YYYY-MM-DD");
  }

  function getSumOfNextPayments() {
    const nextPayments =
      extendedPaymentsByDueDate[getEarliestDueDateAsString()];
    return nextPayments.reduce(
      (sum, extendedPayment) => sum + extendedPayment.payment.amount,
      0,
    );
  }

  function getMandateRefForNextPayments() {
    const nextPayments =
      extendedPaymentsByDueDate[getEarliestDueDateAsString()];
    return nextPayments[0].payment.mandateRef;
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
              <small>
                am {formatDateText(new Date(getEarliestDueDateAsString()))}
                <br />
                {getMandateRefForNextPayments()}
              </small>
            </>
          )}
        </Card.Body>
      </Card>
      <FuturePaymentsModal
        extendedPaymentsByDueDate={extendedPaymentsByDueDate}
        show={showModal}
        onHide={() => setShowModal(false)}
        loading={loading}
      ></FuturePaymentsModal>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default FuturePaymentsCard;
