import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import BestellWizardCardTitle from "../BestellWizardCardTitle.tsx";
import { BestellWizardConfirmOrderResponse } from "../../api-client";

interface BestellWizardEndProps {
  theme: TapirTheme;
  response: BestellWizardConfirmOrderResponse;
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
      <p>Bestellung bestätigt: {response.orderConfirmed ? "Ja" : "Nein"}</p>
      <ul>
        {Object.entries(response.errors).map(([field, messages]) => (
          <li key={field}>
            {field}
            <ul>
              {messages.map((message) => (
                <li>{message}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </>
  );
};

export default BestellWizardEnd;
