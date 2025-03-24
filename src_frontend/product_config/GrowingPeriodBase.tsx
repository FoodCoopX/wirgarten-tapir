import React, { useState } from "react";
import { GenericExportsApi } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import GrowingPeriodModal from "./GrowingPeriodModal.tsx";
import { getPeriodId } from "./get_period_id.ts";

interface GrowingPeriodBaseProps {
  csrfToken: string;
}

const GrowingPeriodBase: React.FC<GrowingPeriodBaseProps> = ({ csrfToken }) => {
  const api = useApi(GenericExportsApi, csrfToken);
  const [showModal, setShowModal] = useState(false);

  function onClick() {
    if (!getPeriodId()) {
      alert(
        "Du musst erst die Vertragsperiode die du editieren möchtest auswählen.",
      );
      return;
    }
    setShowModal(true);
  }
  return (
    <>
      <TapirButton
        icon={"edit"}
        variant={"outline-primary"}
        onClick={onClick}
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
