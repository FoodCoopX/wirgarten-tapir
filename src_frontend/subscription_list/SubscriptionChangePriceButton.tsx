import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import SubscriptionChangePriceModal from "./SubscriptionChangePriceModal.tsx";

interface SubscriptionChangePriceButtonProps {
  csrfToken: string;
}

const SubscriptionChangePriceButton: React.FC<
  SubscriptionChangePriceButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [subscriptionId, setSubscriptionId] = useState();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"euro"}
        variant={"outline-primary"}
        onClick={() => {
          const subscriptionId = getParameterFromUrl("contract");
          if (!subscriptionId) {
            alert("Du musst erst der Vertrag auswählen.");
            return;
          }
          setSubscriptionId(subscriptionId);
          setShowModal(true);
        }}
        tooltip={"Betrag ändern"}
      />
      {subscriptionId && (
        <SubscriptionChangePriceModal
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

export default SubscriptionChangePriceButton;
