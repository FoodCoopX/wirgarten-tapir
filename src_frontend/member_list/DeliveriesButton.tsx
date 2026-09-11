import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import DeliveryListModal from "./DeliveryListModal.tsx";

interface DeliveriesButtonProps {
  csrfToken: string;
}

const DeliveriesButton: React.FC<DeliveriesButtonProps> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState();

  return (
    <>
      <TapirButton
        icon={"local_shipping"}
        variant={"outline-info"}
        onClick={() => {
          const memberId = getParameterFromUrl("member");
          if (!memberId) {
            alert("Du musst erst das Mitglied auswählen.");
            return;
          }
          setMemberId(memberId);
          setShowModal(true);
        }}
        tooltip={"Lieferreihe anzeigen"}
        tootlipPosition={"bottom"}
      />
      {memberId && (
        <DeliveryListModal
          memberId={memberId}
          csrfToken={csrfToken}
          show={showModal}
          onHide={() => setShowModal(false)}
        />
      )}
    </>
  );
};

export default DeliveriesButton;
