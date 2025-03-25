import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import GrowingPeriodModal from "./GrowingPeriodModal.tsx";
import { getPeriodIdFromUrl } from "./get_period_id_from_url.ts";

interface GrowingPeriodBaseProps {
  csrfToken: string;
}

const GrowingPeriodBase: React.FC<GrowingPeriodBaseProps> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);

  function onClick() {
    if (!getPeriodIdFromUrl()) {
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
