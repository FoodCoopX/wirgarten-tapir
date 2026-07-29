import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import SubscriptionChangeDatesModal from "./SubscriptionChangeDatesModal.tsx";

interface SubscriptionChangeDatesButtonProps {
  csrfToken: string;
}

const SubscriptionChangeDatesButton: React.FC<
  SubscriptionChangeDatesButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [subscriptionId, setSubscriptionId] = useState();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"edit_calendar"}
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
        tooltip={"Vertragsstart-anpassen/Sonderkündigung"}
        tootlipPosition={"bottom"}
      />
      {subscriptionId && (
        <SubscriptionChangeDatesModal
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

export default SubscriptionChangeDatesButton;
