import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import SubscriptionTrialPeriodModal from "./SubscriptionTrialPeriodModal.tsx";

interface SubscriptionTrialPeriodButtonProps {
  csrfToken: string;
}

const SubscriptionTrialPeriodButton: React.FC<
  SubscriptionTrialPeriodButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [subscriptionId, setSubscriptionId] = useState<string>();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"hourglass_empty"}
        variant={"outline-primary"}
        onClick={() => {
          const selectedSubscriptionId = getParameterFromUrl("contract");
          if (!selectedSubscriptionId) {
            alert("Du musst erst der Vertrag auswählen.");
            return;
          }
          setSubscriptionId(selectedSubscriptionId);
          setShowModal(true);
        }}
        tooltip={"Probezeit aktivieren/deaktivieren"}
      />
      {subscriptionId && (
        <SubscriptionTrialPeriodModal
          csrfToken={csrfToken}
          show={showModal}
          subscriptionId={subscriptionId}
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

export default SubscriptionTrialPeriodButton;
