import React, { useEffect, useRef, useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Accordion } from "react-bootstrap";
import NextStepButton from "../components/NextStepButton.tsx";
import { scrollIntoView } from "../utils/scrollIntoView.ts";
import TapirCheckbox from "../components/TapirCheckbox.tsx";

interface Step11LegalProps {
  settings: BestellWizardSettings;
  cancellationPolicyRead: boolean;
  setCancellationPolicyRead: (read: boolean) => void;
  privacyPolicyRead: boolean;
  setPrivacyPolicyRead: (read: boolean) => void;
  active: boolean;
  goToNextStep: () => void;
}

const Step11Legal: React.FC<Step11LegalProps> = ({
  settings,
  cancellationPolicyRead,
  setCancellationPolicyRead,
  privacyPolicyRead,
  setPrivacyPolicyRead,
  active,
  goToNextStep,
}) => {
  const scrollDiv = useRef<HTMLDivElement>(null);
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

  useEffect(() => {
    if (!active || !scrollDiv.current) {
      return;
    }

    scrollDiv.current.scrollTop = 0;
  }, [active]);

  function validate() {
    setShowValidation(true);

    if (cancellationPolicyRead && privacyPolicyRead) {
      goToNextStep();
    }
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
              label={
                "Ja, ich habe die Widerrufsbelehrung zur Kenntnis genommen."
              }
              showError={showValidation && !cancellationPolicyRead}
            />
          </Accordion.Header>
          <Accordion.Body>
            <span
              dangerouslySetInnerHTML={{
                __html: settings.revocationRightsExplanation,
              }}
            />
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
      <Accordion style={{ width: "100%" }}>
        <Accordion.Item eventKey={"privacy"} onClick={scrollIntoView}>
          <Accordion.Header>
            <TapirCheckbox
              controlId={"legal_privacy"}
              checked={privacyPolicyRead}
              onChange={setPrivacyPolicyRead}
              label={
                "Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."
              }
              showError={showValidation && !privacyPolicyRead}
            />
          </Accordion.Header>
          <Accordion.Body>
            Wir behandeln deine Daten vertraulich, verwenden diese nur im Rahmen
            der Mitgliederverwaltung und geben sie nicht an Dritte weiter.
            Unsere Datenschutzerklärung kannst du hier einsehen:{" "}
            <a href={settings.strings.privacyPolicyUrl} target="_blank">
              Datenschutzerklärung
            </a>
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>

      <NextStepButton onClick={validate} />
    </>
  );
};

export default Step11Legal;
