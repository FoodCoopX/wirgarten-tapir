import React, { useEffect, useRef } from "react";
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

  useEffect(() => {
    if (!active || !scrollDiv.current) {
      return;
    }

    scrollDiv.current.scrollTop = 0;
  }, [active]);

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

      <NextStepButton
        onClick={goToNextStep}
        disabled={!cancellationPolicyRead || !privacyPolicyRead}
      />
    </>
  );
};

export default Step11Legal;
