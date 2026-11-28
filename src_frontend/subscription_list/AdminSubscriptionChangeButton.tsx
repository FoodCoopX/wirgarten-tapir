import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import AdminSubscriptionChangeModal from "./AdminSubscriptionChangeModal.tsx";

const AdminSubscriptionChangeButton: React.FC = () => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"edit_note"}
        variant={"outline-primary"}
        onClick={() => setShowModal(true)}
        tooltip={"Anteilsgröße zu einem bestimmten Datum verändern"}
        tootlipPosition={"bottom"}
      />
      {showModal && (
        <AdminSubscriptionChangeModal
          onHide={() => setShowModal(false)}
          setToastDatas={setToastDatas}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default AdminSubscriptionChangeButton;
