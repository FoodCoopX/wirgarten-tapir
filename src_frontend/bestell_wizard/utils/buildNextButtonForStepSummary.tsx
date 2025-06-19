import BestellWizardNextButton from "../components/BestellWizardNextButton.tsx";
import React from "react";

export function buildNextButtonForStepSummary(
  privacyPolicyRead: boolean,
  waitingListModeEnabled: boolean,
  cancellationPolicyRead: boolean,
  confirmOrderLoading: boolean,
  onConfirmOrder: () => void,
) {
  let text = "Bestellung abschließen";
  if (waitingListModeEnabled) {
    text = "Warteliste-Eintrag bestätigen";
  }
  if (!privacyPolicyRead) {
    text = "Du musst die Datenschutzerklärung bestätigen";
  }
  if (!cancellationPolicyRead && !waitingListModeEnabled) {
    text = "Du musst die Widerrufsbelehrung bestätigen";
  }

  let allRead = privacyPolicyRead;
  if (!waitingListModeEnabled) {
    allRead = allRead && cancellationPolicyRead;
  }

  const params = {
    disabled: !allRead,
    loading: confirmOrderLoading,
    text: text,
    icon: "check",
  };
  return (
    <BestellWizardNextButton params={params} onNextClicked={onConfirmOrder} />
  );
}
