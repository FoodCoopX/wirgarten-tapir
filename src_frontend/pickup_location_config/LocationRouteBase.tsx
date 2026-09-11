import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import LocationRouteModal from "./LocationRouteModal.tsx";

interface LocationRouteProps {
  csrfToken: string;
}

const LocationRouteBase: React.FC<LocationRouteProps> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <div className={"d-flex gap-2"}>
      <TapirButton
        icon={"local_shipping"}
        variant={"outline-primary"}
        onClick={() => setShowModal(true)}
        text={"Ausfahrrunden verwalten"}
      />
      <LocationRouteModal
        csrfToken={csrfToken}
        show={showModal}
        onHide={() => setShowModal(false)}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default LocationRouteBase;
