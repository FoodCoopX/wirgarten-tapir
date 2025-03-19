import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import "dayjs/locale/de";
import SubscriptionCancellationModal from "./SubscriptionCancellationModal.tsx";

interface SubscriptionCancellationButtonProps {
  csrfToken: string;
  memberId: string;
  productTypeName: string;
}

const SubscriptionCancellationButton: React.FC<
  SubscriptionCancellationButtonProps
> = ({ csrfToken, memberId, productTypeName }) => {
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <TapirButton
        variant={"outline-primary"}
        icon={"contract_delete"}
        fontSize={24}
        onClick={() => {
          setShowModal(true);
        }}
      />
      <SubscriptionCancellationModal
        memberId={memberId}
        csrfToken={csrfToken}
        productTypeName={productTypeName}
        show={showModal}
        onHide={() => setShowModal(false)}
      />
    </>
  );
};

export default SubscriptionCancellationButton;
