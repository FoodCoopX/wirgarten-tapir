import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import { OrderConfirmationResponse } from "../../api-client";

interface BestellWizardEndProps {
  theme: TapirTheme;
  response: OrderConfirmationResponse;
}

const BestellWizardEnd: React.FC<BestellWizardEndProps> = ({
  theme,
  response,
}) => {
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
