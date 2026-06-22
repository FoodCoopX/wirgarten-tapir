import dayjs from "dayjs";
import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { PaymentsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import FuturePaymentsModal from "../member_profile/future_payments/FuturePaymentsModal.tsx";
import { sortGroupedTransactions } from "../member_profile/future_payments/sortGroupedTransactions.ts";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import { TransactionsByDueDate } from "../types/TransactionsByDueDate.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface PaymentsButtonProps {
  csrfToken: string;
}

const PaymentsButton: React.FC<PaymentsButtonProps> = ({ csrfToken }) => {
  const paymentsApi = useApi(PaymentsApi, csrfToken);
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState();
  const [loading, setLoading] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [trialPeriodEnabled, setTrialPeriodEnabled] = useState(false);
  const [transactionsByDueDate, setTransactionsByDueDate] =
    useState<TransactionsByDueDate>({});

  useEffect(() => {
    if (memberId === undefined) return;

    setLoading(true);

    loadData();
  }, [memberId]);

  function loadData() {
    setLoading(true);

    paymentsApi
      .paymentsApiMemberFuturePaymentsRetrieve({ memberId: memberId })
      .then((response) => {
        setTrialPeriodEnabled(response.trialPeriodEnabled);

        const groupedTransactions: TransactionsByDueDate = {};

        const extendedPayments = response.payments.toSorted(
          (a, b) => a.payment.dueDate.getTime() - b.payment.dueDate.getTime(),
        );
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
  }

  return (
    <>
      <TapirButton
        icon={"payments"}
        variant={"outline-info"}
        onClick={() => {
          const memberId = getParameterFromUrl("member");
          if (!memberId) {
            alert("Du musst erst das Mitglied auswählen.");
            return;
          }
          setMemberId(memberId);
          setShowModal(true);
        }}
        tooltip={"Zahlungsreihe anzeigen"}
        tootlipPosition={"bottom"}
        loading={loading}
      />
      {memberId && (
        <FuturePaymentsModal
          show={showModal}
          onHide={() => setShowModal(false)}
          loading={loading}
          csrfToken={csrfToken}
          memberId={memberId}
          setToastDatas={setToastDatas}
          trialPeriodEnabled={trialPeriodEnabled}
          transactionsByDueDate={transactionsByDueDate}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default PaymentsButton;
