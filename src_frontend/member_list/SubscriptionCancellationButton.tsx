import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import SubscriptionCancellationModal from "../member_profile/subscription_cancellation/SubscriptionCancellationModal";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";

interface SubscriptionCancellationButtonProps {
  csrfToken: string;
}

const SubscriptionCancellationButton: React.FC<
  SubscriptionCancellationButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"contract_delete"}
        variant={"outline-danger"}
        onClick={() => {
          const memberId = getParameterFromUrl("member");
          if (!memberId) {
            alert("Du musst erst das Mitglied auswählen.");
            return;
          }
          setMemberId(getParameterFromUrl("member"));
          setShowModal(true);
        }}
        tooltip={"Verträge kündigen"}
        tootlipPosition={"bottom"}
      />
      {memberId && (
        <SubscriptionCancellationModal
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

export default SubscriptionCancellationButton;
