import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import PickupLocationCapacityModal from "./PickupLocationCapacityModal.tsx";
import PickupLocationDeliveryChargeModal from "./PickupLocationDeliveryChargeModal.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";

interface ProductBaseProps {
  csrfToken: string;
}

const URL_PARAMETER_PICKUP_LOCATION_ID = "selected";

const PickupLocationCapacityBase: React.FC<ProductBaseProps> = ({
  csrfToken,
}) => {
  const [showCapacityModal, setShowCapacityModal] = useState(false);
  const [showDeliveryChargeModal, setShowDeliveryChargeModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function requireSelectedLocation(): boolean {
    if (!getParameterFromUrl(URL_PARAMETER_PICKUP_LOCATION_ID)) {
      alert("Du musst erst die Abholort das du editieren möchtest auswählen.");
      return false;
    }
    return true;
  }

  function onCapacityClick() {
    if (!requireSelectedLocation()) return;
    setShowCapacityModal(true);
  }

  function onDeliveryChargeClick() {
    if (!requireSelectedLocation()) return;
    setShowDeliveryChargeModal(true);
  }

  return (
    <div className={"d-flex"}>
      <TapirButton
        icon={"warehouse"}
        variant={"outline-primary"}
        onClick={onCapacityClick}
        tooltip={"Kapazitäten bearbeiten"}
      />
      <TapirButton
        icon={"euro"}
        variant={"outline-primary"}
        onClick={onDeliveryChargeClick}
        tooltip={"Lieferzuschlag verwalten"}
      />
      <PickupLocationCapacityModal
        csrfToken={csrfToken}
        show={showCapacityModal}
        onHide={() => setShowCapacityModal(false)}
        setToastDatas={setToastDatas}
      />
      <PickupLocationDeliveryChargeModal
        csrfToken={csrfToken}
        show={showDeliveryChargeModal}
        onHide={() => setShowDeliveryChargeModal(false)}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default PickupLocationCapacityBase;
