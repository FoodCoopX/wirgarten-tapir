import React, { useEffect, useRef, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { replaceTokens } from "../utils/replaceTokens.ts";
import StepTitle from "../components/StepTitle.tsx";

interface Step6BCoopSharesProps {
  goToNextStep: () => void;
  selectedNumberOfCoopShares: number;
  setSelectedNumberOfCoopShares: (nbShares: number) => void;
  statuteAccepted: boolean;
  setStatuteAccepted: (statuteRead: boolean) => void;
  minimumNumberOfShares: number;
  studentStatusEnabled: boolean;
  setStudentStatusEnabled: (status: boolean) => void;
  settings: BestellWizardSettings;
  firstName: string;
  active: boolean;
}

const Step6BCoopShares: React.FC<Step6BCoopSharesProps> = ({
  goToNextStep,
  selectedNumberOfCoopShares,
  setSelectedNumberOfCoopShares,
  minimumNumberOfShares,
  studentStatusEnabled,
  setStudentStatusEnabled,
  settings,
  firstName,
  statuteAccepted,
  setStatuteAccepted,
  active,
}) => {
  const [statuteRead, setStatuteRead] = useState(false);
  const [commitmentChecked, setCommitmentChecked] = useState(false);

  const scrollDiv = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !scrollDiv.current) {
      return;
    }

    scrollDiv.current.scrollTop = 0;
  }, [active]);

  useEffect(() => {
    setStatuteAccepted(statuteRead && commitmentChecked);
  }, [statuteRead, commitmentChecked]);

  function isGoNextButtonDisabled() {
    if (studentStatusEnabled) {
      return false;
    }

    if (!statuteAccepted) {
      return true;
    }

    return selectedNumberOfCoopShares < minimumNumberOfShares;
  }

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
              title={replaceTokens(settings.strings.step6bTitle, firstName)}
            />
            <div>
              {settings.strings.step6bText && (
                <p
                  className={"text-center"}
                  dangerouslySetInnerHTML={getHtmlDescription(
                    settings.strings.step6bText,
                  )}
                />
              )}
            </div>
            <small className={"d-flex flex-row align-items-center gap-2"}>
              <TapirButton
                icon={"remove"}
                variant={"outline-secondary"}
                onClick={() => {
                  setSelectedNumberOfCoopShares(
                    Math.max(
                      minimumNumberOfShares,
                      selectedNumberOfCoopShares - 1,
                    ),
                  );
                }}
                disabled={selectedNumberOfCoopShares <= minimumNumberOfShares}
                size={"sm"}
              />
              <Form.Group style={{ maxWidth: "30px" }}>
                <Form.Control
                  min={minimumNumberOfShares}
                  step={1}
                  value={selectedNumberOfCoopShares}
                  onChange={(event) =>
                    setSelectedNumberOfCoopShares(parseInt(event.target.value))
                  }
                  disabled={true}
                  size={"sm"}
                />
              </Form.Group>
              <TapirButton
                icon={"add"}
                variant={"outline-secondary"}
                onClick={() => {
                  setSelectedNumberOfCoopShares(selectedNumberOfCoopShares + 1);
                }}
                size={"sm"}
              />
              <span>
                {" × "}
                {formatCurrency(settings.priceOfAShare)} ={" "}
              </span>
              <span>
                <strong>
                  {formatCurrency(
                    selectedNumberOfCoopShares * settings.priceOfAShare,
                  )}
                </strong>
              </span>
            </small>
            {settings.studentStatusAllowed && (
              <div>
                <Form.Check
                  id={"studentStatus"}
                  checked={studentStatusEnabled}
                  onChange={(event) => {
                    setStudentStatusEnabled(event.target.checked);
                    setSelectedNumberOfCoopShares(
                      event.target.checked ? 0 : minimumNumberOfShares,
                    );
                  }}
                  label={
                    "Ich bin Student*in und kann keine Genossenschaftsanteile zeichnen"
                  }
                />
                {studentStatusEnabled && (
                  <Form.Text>
                    Die Immatrikulationsbescheinigung muss per Mail an{" "}
                    <a href={"mailto:" + settings.contactMailAddress}>
                      {settings.contactMailAddress}
                    </a>{" "}
                    gesendet werden.
                  </Form.Text>
                )}
              </div>
            )}
            <Form.Check
              id={"statuteRead"}
              checked={statuteRead && !studentStatusEnabled}
              onChange={(event) => setStatuteRead(event.target.checked)}
              label={settings.strings.step6cCheckboxStatute}
              disabled={studentStatusEnabled}
            />
            <Form.Check
              id={"commitment"}
              checked={commitmentChecked && !studentStatusEnabled}
              onChange={(event) => setCommitmentChecked(event.target.checked)}
              label={settings.strings.step6cCheckboxCommitment}
              disabled={studentStatusEnabled}
            />
          </div>
        </div>
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
            icon={"keyboard_arrow_down"}
            disabled={isGoNextButtonDisabled()}
          />
        </div>
      </div>
    </>
  );
};

export default Step6BCoopShares;
