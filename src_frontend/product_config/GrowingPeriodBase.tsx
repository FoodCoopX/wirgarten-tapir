import React, { useState } from "react";
import { GenericExportsApi } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import GrowingPeriodModal from "./GrowingPeriodModal.tsx";

interface GrowingPeriodBaseProps {
  csrfToken: string;
}

const GrowingPeriodBase: React.FC<GrowingPeriodBaseProps> = ({ csrfToken }) => {
  const api = useApi(GenericExportsApi, csrfToken);
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <TapirButton
        icon={"edit"}
        variant={"outline-primary"}
        onClick={() => setShowModal(true)}
      />
      <GrowingPeriodModal
        csrfToken={csrfToken}
        show={showModal}
        onHide={() => setShowModal(false)}
      />
    </>
  );
};

export default GrowingPeriodBase;
