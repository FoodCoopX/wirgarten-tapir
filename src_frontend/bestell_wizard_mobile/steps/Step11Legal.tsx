import React, { useEffect, useRef } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { replaceTokens } from "../utils/replaceTokens.ts";
import StepTitle from "../components/StepTitle.tsx";
import { Form } from "react-bootstrap";

interface Step11LegalProps {
  settings: BestellWizardSettings;
  cancellationPolicyRead: boolean;
  setCancellationPolicyRead: (read: boolean) => void;
  privacyPolicyRead: boolean;
  setPrivacyPolicyRead: (read: boolean) => void;
  active: boolean;
  goToNextStep: () => void;
  firstName: string;
}

const Step11Legal: React.FC<Step11LegalProps> = ({
  settings,
  cancellationPolicyRead,
  setCancellationPolicyRead,
  privacyPolicyRead,
  setPrivacyPolicyRead,
  active,
  goToNextStep,
  firstName,
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
      <div
        style={{ height: "80dvh", display: "flex", flexDirection: "column" }}
        className={"d-flex flex-column gap-2 mx-2"}
      >
        <div
          style={{
            maxHeight: "70dvh",
            overflowY: "scroll",
          }}
          ref={scrollDiv}
        >
          <div
            className={
              "d-flex align-items-center justify-content-center gap-2 flex-column mx-4"
            }
            style={{ minHeight: "70dvh" }}
          >
            <StepTitle
              title={replaceTokens(settings.strings.step11Title, firstName)}
            />
            <Form.Group controlId={"cancellation"}>
              <Form.Check
                onChange={(event) =>
                  setCancellationPolicyRead(event.target.checked)
                }
                required={true}
                checked={cancellationPolicyRead}
                label={
                  "Ja, ich habe die Widerrufsbelehrung zur Kenntnis genommen."
                }
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
                label={
                  "Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."
                }
              />
              {settings.revocationRightsExplanation && (
                <Form.Text>
                  Wir behandeln deine Daten vertraulich, verwenden diese nur im
                  Rahmen der Mitgliederverwaltung und geben sie nicht an Dritte
                  weiter. Unsere Datenschutzerklärung kannst du hier einsehen:{" "}
                  <a href={settings.strings.privacyPolicyUrl} target="_blank">
                    Datenschutzerklärung
                  </a>
                </Form.Text>
              )}
            </Form.Group>
          </div>
        </div>
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
            icon={"keyboard_arrow_down"}
            disabled={!cancellationPolicyRead || !privacyPolicyRead}
          />
        </div>
      </div>
    </>
  );
};

export default Step11Legal;
