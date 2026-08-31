import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import { URL_PARAMETER_PICKUP_LOCATION_ID } from "./constants.ts";
import PickupLocationGrowingPeriodModal from "./PickupLocationGrowingPeriodModal.tsx";

interface PickupLocationGrowingPeriodBaseProps {
  csrfToken: string;
  enabled: boolean;
}

const PickupLocationGrowingPeriodBase: React.FC<
  PickupLocationGrowingPeriodBaseProps
> = ({ csrfToken, enabled }) => {
  const [showModal, setShowModal] = useState(false);
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(
    null,
  );
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  if (!enabled) {
    return null;
  }

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

  function onClick() {
    const pickupLocationId = requireSelectedLocation();
    if (!pickupLocationId) return;
    setSelectedLocationId(pickupLocationId);
    setShowModal(true);
  }

  return (
    <div className={"d-flex gap-2"}>
      <TapirButton
        icon={"calendar_month"}
        variant={"outline-primary"}
        onClick={onClick}
        tooltip={"Vertragsperioden zuordnen"}
      />
      {selectedLocationId && (
        <PickupLocationGrowingPeriodModal
          csrfToken={csrfToken}
          show={showModal}
          onHide={() => setShowModal(false)}
          setToastDatas={setToastDatas}
          pickupLocationId={selectedLocationId}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default PickupLocationGrowingPeriodBase;