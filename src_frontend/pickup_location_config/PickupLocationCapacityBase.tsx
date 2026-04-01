import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import PickupLocationCapacityModal from "./PickupLocationCapacityModal.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";

interface ProductBaseProps {
  csrfToken: string;
}

const PickupLocationCapacityBase: React.FC<ProductBaseProps> = ({
  csrfToken,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

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
        tooltip={"Kapazitäten bearbeiten"}
      />
      <PickupLocationCapacityModal
        csrfToken={csrfToken}
        show={showModal}
        onHide={() => setShowModal(false)}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default PickupLocationCapacityBase;
