import React, { useEffect, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Form } from "react-bootstrap";

interface Step6CCoopLegalProps {
  goToNextStep: () => void;
  statuteAccepted: boolean;
  setStatuteAccepted: (statuteRead: boolean) => void;
  settings: BestellWizardSettings;
}

const Step6CCoopLegal: React.FC<Step6CCoopLegalProps> = ({
  goToNextStep,
  statuteAccepted,
  setStatuteAccepted,
  settings,
}) => {
  const [statuteRead, setStatuteRead] = useState(false);
  const [commitmentChecked, setCommitmentChecked] = useState(false);

  useEffect(() => {
    setStatuteAccepted(statuteRead && commitmentChecked);
  }, [statuteRead, commitmentChecked]);
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
        >
          <div
            className={
              "d-flex align-items-center justify-content-center gap-2 flex-column mx-4"
            }
            style={{ minHeight: "70dvh" }}
          >
            <div>
              <Form.Check
                id={"statuteRead"}
                checked={statuteRead}
                onChange={(event) => setStatuteRead(event.target.checked)}
                label={settings.strings.step6cCheckboxStatute}
              />
              <Form.Text>
                <a href={settings.coopStatuteLink}>
                  {settings.coopStatuteLink}
                </a>
                <br />
                {settings.strings.step6cTextStatute}
              </Form.Text>
            </div>
            <div>
              <Form.Check
                id={"commitment"}
                checked={commitmentChecked}
                onChange={(event) => setCommitmentChecked(event.target.checked)}
                label={settings.strings.step6cCheckboxCommitment}
              />
            </div>
          </div>
        </div>
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
            icon={"keyboard_arrow_down"}
            disabled={!statuteAccepted}
          />
        </div>
      </div>
    </>
  );
};

export default Step6CCoopLegal;
