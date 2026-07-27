import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import { URL_PARAMETER_PICKUP_LOCATION_ID } from "./constants.ts";
import PickupLocationCapacityModal from "./PickupLocationCapacityModal.tsx";
import PickupLocationDeliveryChargeModal from "./PickupLocationDeliveryChargeModal.tsx";

interface ProductBaseProps {
  csrfToken: string;
  enableDeliveryCharge: boolean;
}

const PickupLocationCapacityBase: React.FC<ProductBaseProps> = ({
  csrfToken,
  enableDeliveryCharge,
}) => {
  const [showCapacityModal, setShowCapacityModal] = useState(false);
  const [showDeliveryChargeModal, setShowDeliveryChargeModal] = useState(false);
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(
    null,
  );
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function requireSelectedLocation(): string | null {
    const pickupLocationId = getParameterFromUrl(
      URL_PARAMETER_PICKUP_LOCATION_ID,
    );
    if (!pickupLocationId) {
      alert("Du musst erst die Abholort das du editieren möchtest auswählen.");
      return null;
    }
    return pickupLocationId;
  }

  function onCapacityClick() {
    const pickupLocationId = requireSelectedLocation();
    if (!pickupLocationId) return;
    setSelectedLocationId(pickupLocationId);
    setShowCapacityModal(true);
  }

  function onDeliveryChargeClick() {
    const pickupLocationId = requireSelectedLocation();
    if (!pickupLocationId) return;
    setSelectedLocationId(pickupLocationId);
    setShowDeliveryChargeModal(true);
  }

  return (
    <div className={"d-flex gap-2"}>
      <TapirButton
        icon={"warehouse"}
        variant={"outline-primary"}
        onClick={onCapacityClick}
        tooltip={"Kapazitäten bearbeiten"}
      />
      {enableDeliveryCharge && (
        <TapirButton
          icon={"euro"}
          variant={"outline-primary"}
          onClick={onDeliveryChargeClick}
          tooltip={"Lieferzuschlag verwalten"}
        />
      )}
      {selectedLocationId && (
        <>
          <PickupLocationCapacityModal
            csrfToken={csrfToken}
            show={showCapacityModal}
            onHide={() => setShowCapacityModal(false)}
            setToastDatas={setToastDatas}
            pickupLocationId={selectedLocationId}
          />
          {enableDeliveryCharge && (
            <PickupLocationDeliveryChargeModal
              csrfToken={csrfToken}
              show={showDeliveryChargeModal}
              onHide={() => setShowDeliveryChargeModal(false)}
              setToastDatas={setToastDatas}
              pickupLocationId={selectedLocationId}
            />
          )}
        </>
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default PickupLocationCapacityBase;
