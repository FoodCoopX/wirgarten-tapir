import React, { useEffect, useState } from "react";
import { PaymentsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import PaymentExportExclusionOverviewModal from "./PaymentExportExclusionOverviewModal.tsx";

interface PaymentExportExclusionOverviewButtonProps {
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const PaymentExportExclusionOverviewButton: React.FC<
  PaymentExportExclusionOverviewButtonProps
> = ({ setToastDatas }) => {
  const api = useApi(PaymentsApi, "unused");
  const [numberOfPeriods, setNumberOfPeriods] = useState<number | undefined>(
    undefined,
  );
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    api
      .paymentsApiPaymentExportExclusionPeriodsOverviewList({
        includeExpired: false,
        limit: 1,
        offset: 0,
      })
      .then((response) => setNumberOfPeriods(response.count))
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Ausschlüsse vom Zahlungsexport",
          setToastDatas,
        ),
      );
  }, []);

  if (numberOfPeriods === undefined) {
    return null;
  }

  return (
    <>
      <TapirButton
        variant={"outline-secondary"}
        text={`Ausschlüsse vom Zahlungsexport: ${numberOfPeriods}`}
        icon={"event_busy"}
        onClick={() => setShowModal(true)}
      />
      <PaymentExportExclusionOverviewModal
        show={showModal}
        onHide={() => setShowModal(false)}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default PaymentExportExclusionOverviewButton;
