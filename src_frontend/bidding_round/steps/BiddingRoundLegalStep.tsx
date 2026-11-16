import React, { useEffect, useState } from "react";
import { Accordion } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import CheckboxWithExplanation from "../../bestell_wizard_mobile/components/CheckboxWithExplanation.tsx";
import TapirCheckbox from "../../bestell_wizard_mobile/components/TapirCheckbox.tsx";
import { scrollIntoView } from "../../bestell_wizard_mobile/utils/scrollIntoView.ts";
import NextStepButton from "../../components/mobile_wizard/NextStepButton.tsx";

interface BiddingRoundLegalStepProps {
  settings: BestellWizardSettings;
  cancellationPolicyRead: boolean;
  setCancellationPolicyRead: (value: boolean) => void;
  contractAccepted: boolean;
  setContractAccepted: (value: boolean) => void;
  privacyPolicyRead: boolean;
  setPrivacyPolicyRead: (value: boolean) => void;
  goToNextStep: () => void;
  stepActive: boolean;
}

const BiddingRoundLegalStep: React.FC<BiddingRoundLegalStepProps> = ({
  settings,
  cancellationPolicyRead,
  setCancellationPolicyRead,
  contractAccepted,
  setContractAccepted,
  privacyPolicyRead,
  setPrivacyPolicyRead,
  goToNextStep,
  stepActive,
}) => {
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (!stepActive) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [stepActive]);

  function showContractPolicy() {
    return settings.explanationCheckboxContractPolicy.trim() !== "";
  }

  function validate() {
    setShowValidation(true);

    if (!cancellationPolicyRead) {
      return;
    }

    if (showContractPolicy() && !contractAccepted) {
      return;
    }

    if (!privacyPolicyRead) {
      return;
    }

    goToNextStep();
  }

  return (
    <>
      <Accordion style={{ width: "100%" }}>
        <Accordion.Item eventKey={"cancellation"} onClick={scrollIntoView}>
          <Accordion.Header>
            <TapirCheckbox
              controlId={"legal_cancellation"}
              checked={cancellationPolicyRead}
              onChange={setCancellationPolicyRead}
              label={settings.strings.step11RevocationLabel}
              showError={showValidation && !cancellationPolicyRead}
            />
          </Accordion.Header>
          <Accordion.Body>
            <span
              dangerouslySetInnerHTML={{
                __html: settings.strings.step11RevocationText,
              }}
            />
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
      {showContractPolicy() && (
        <CheckboxWithExplanation
          controlId={"legal_contract"}
          checked={contractAccepted}
          onChange={setContractAccepted}
          label={settings.labelCheckboxContractPolicy}
          explanation={settings.explanationCheckboxContractPolicy}
          showError={showValidation && !contractAccepted}
        />
      )}
      <Accordion style={{ width: "100%" }}>
        <Accordion.Item eventKey={"privacy"} onClick={scrollIntoView}>
          <Accordion.Header>
            <TapirCheckbox
              controlId={"legal_privacy"}
              checked={privacyPolicyRead}
              onChange={setPrivacyPolicyRead}
              label={settings.strings.step11PrivacyPolicyLabel}
              showError={showValidation && !privacyPolicyRead}
            />
          </Accordion.Header>
          <Accordion.Body>
            <span
              dangerouslySetInnerHTML={{
                __html: settings.strings.step11PrivacyPolicyText.replace(
                  "{link_zu_datenschutzerklärung}",
                  settings.strings.privacyPolicyUrl,
                ),
              }}
            />
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
      <NextStepButton onClick={validate} stepActive={stepActive} />
    </>
  );
};

export default BiddingRoundLegalStep;
