import React, { useState } from "react";
import "dayjs/locale/de";
import TapirButton from "../components/TapirButton.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import SubscriptionAddContractModal from "./SubscriptionAddContractModal.tsx";

interface SubscriptionAddContractButtonProps {
  csrfToken: string;
}

const SubscriptionAddContractButton: React.FC<
  SubscriptionAddContractButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState<string>();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"post_add"}
        variant={"outline-primary"}
        onClick={() => {
          const memberId = getParameterFromUrl("member");
          if (!memberId) {
            alert("Du musst erst ein Mitglied auswählen. Du kannst rechts unter 'Mitglied' suchen, oder über die Mitgliederliste eines auswählen und auf 'Verträge anzeigen'.");
            return;
          }
          setMemberId(memberId);
          setShowModal(true);
        }}
        tooltip={"Vertrag hinzufügen"}
      />
      {memberId && (
        <SubscriptionAddContractModal
          csrfToken={csrfToken}
          show={showModal}
          memberId={memberId}
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

export default SubscriptionAddContractButton;
