import React, { useEffect, useRef } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Form } from "react-bootstrap";
import NextStepButton from "../components/NextStepButton.tsx";

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
      <Form.Group controlId={"cancellation"}>
        <Form.Check
          onChange={(event) => setCancellationPolicyRead(event.target.checked)}
          required={true}
          checked={cancellationPolicyRead}
          label={"Ja, ich habe die Widerrufsbelehrung zur Kenntnis genommen."}
        />
        {settings.revocationRightsExplanation && (
          <Form.Text>
            <span
              dangerouslySetInnerHTML={{
                __html: settings.revocationRightsExplanation,
              }}
            />
          </Form.Text>
        )}
      </Form.Group>
      <Form.Group controlId={"privacy"}>
        <Form.Check
          onChange={(event) => setPrivacyPolicyRead(event.target.checked)}
          required={true}
          checked={privacyPolicyRead}
          label={"Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."}
        />
        {settings.revocationRightsExplanation && (
          <Form.Text>
            Wir behandeln deine Daten vertraulich, verwenden diese nur im Rahmen
            der Mitgliederverwaltung und geben sie nicht an Dritte weiter.
            Unsere Datenschutzerklärung kannst du hier einsehen:{" "}
            <a href={settings.strings.privacyPolicyUrl} target="_blank">
              Datenschutzerklärung
            </a>
          </Form.Text>
        )}
      </Form.Group>
      <NextStepButton
        onClick={goToNextStep}
        disabled={!cancellationPolicyRead || !privacyPolicyRead}
      />
    </>
  );
};

export default Step11Legal;
