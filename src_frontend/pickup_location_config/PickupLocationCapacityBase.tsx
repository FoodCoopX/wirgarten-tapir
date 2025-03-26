import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import PickupLocationCapacityModal from "./PickupLocationCapacityModal.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";

interface ProductBaseProps {
  csrfToken: string;
}

const PickupLocationCapacityBase: React.FC<ProductBaseProps> = ({
  csrfToken,
}) => {
  const [showModal, setShowModal] = useState(false);

  const URL_PARAMETER_PICKUP_LOCATION_ID = "selected";

  function onClick() {
    if (!getParameterFromUrl(URL_PARAMETER_PICKUP_LOCATION_ID)) {
      alert("Du musst erst die Abholort das du editieren möchtest auswählen.");
      return;
    }
    setShowModal(true);
  }
  return (
    <>
      <TapirButton
        icon={"warehouse"}
        variant={"outline-primary"}
        onClick={onClick}
      />
      <PickupLocationCapacityModal
        csrfToken={csrfToken}
        show={showModal}
        onHide={() => setShowModal(false)}
      />
    </>
  );
};

export default PickupLocationCapacityBase;
