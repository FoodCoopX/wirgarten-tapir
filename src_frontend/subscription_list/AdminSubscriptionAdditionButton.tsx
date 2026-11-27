import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import AdminSubscriptionAdditionModal from "./AdminSubscriptionAdditionModal.tsx";

const AdminSubscriptionAdditionButton: React.FC = () => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"post_add"}
        variant={"outline-primary"}
        onClick={() => setShowModal(true)}
        tooltip={"Vertrag hinzufügen"}
        tootlipPosition={"bottom"}
      />
      {showModal && (
        <AdminSubscriptionAdditionModal
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

export default AdminSubscriptionAdditionButton;
