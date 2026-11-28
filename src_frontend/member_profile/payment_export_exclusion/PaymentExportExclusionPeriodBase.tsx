import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import PaymentExportExclusionPeriodModal from "./PaymentExportExclusionPeriodModal.tsx";

interface PaymentExportExclusionPeriodBaseProps {
  memberId: string;
}

const PaymentExportExclusionPeriodBase: React.FC<
  PaymentExportExclusionPeriodBaseProps
> = ({ memberId }) => {
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
