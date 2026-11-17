import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import PaymentExportExclusionPeriodModal from "./PaymentExportExclusionPeriodModal.tsx";

interface PaymentExportExclusionPeriodBaseProps {
  memberId: string;
  csrfToken: string;
}

const PaymentExportExclusionPeriodBase: React.FC<
  PaymentExportExclusionPeriodBaseProps
> = ({ memberId, csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        variant={"outline-primary"}
        icon={"edit"}
        size={"sm"}
        onClick={() => setShowModal(true)}
      />
      <PaymentExportExclusionPeriodModal
        memberId={memberId}
        csrfToken={csrfToken}
        setToastDatas={setToastDatas}
        show={showModal}
        onHide={() => setShowModal(false)}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default PaymentExportExclusionPeriodBase;
