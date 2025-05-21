import React, { useState } from "react";
import "dayjs/locale/de";
import SubscriptionCancellationModal from "../member_profile/subscription_cancellation/SubscriptionCancellationModal";
import TapirButton from "../components/TapirButton.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";

interface SubscriptionCancellationButtonProps {
  csrfToken: string;
}

const SubscriptionCancellationButton: React.FC<
  SubscriptionCancellationButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState();

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
      />
      {memberId && (
        <SubscriptionCancellationModal
          csrfToken={csrfToken}
          show={showModal}
          memberId={memberId}
          onHide={() => setShowModal(false)}
        />
      )}
    </>
  );
};

export default SubscriptionCancellationButton;
