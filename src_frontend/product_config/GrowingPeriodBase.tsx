import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import GrowingPeriodModal from "./GrowingPeriodModal.tsx";
import { getPeriodIdFromUrl } from "./get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";

interface GrowingPeriodBaseProps {
  csrfToken: string;
}

const GrowingPeriodBase: React.FC<GrowingPeriodBaseProps> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function onClick() {
    if (!getPeriodIdFromUrl()) {
      alert(
        "Du musst erst die Vertragsperiode die du editieren möchtest auswählen.",
      );
      return;
    }
    setShowModal(true);
  }
  return (
    <>
      <TapirButton
        icon={"edit"}
        variant={"outline-primary"}
        onClick={onClick}
      />
      <GrowingPeriodModal
        csrfToken={csrfToken}
        show={showModal}
        onHide={() => setShowModal(false)}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default GrowingPeriodBase;
