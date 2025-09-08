import React from "react";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import { OrderConfirmationResponse } from "../../api-client";

interface BestellWizardEndProps {
  response: OrderConfirmationResponse;
}

const BestellWizardEnd: React.FC<BestellWizardEndProps> = ({ response }) => {
  return (
    <>
      <BestellWizardCardTitle
        text={"BestellWizard Bestellung Bestätigung Debug"}
      />
      {response && (
        <>
          <p>Bestellung bestätigt: {response.orderConfirmed ? "Ja" : "Nein"}</p>
          {response.error && <p>{response.error}</p>}
        </>
      )}
    </>
  );
};

export default BestellWizardEnd;
