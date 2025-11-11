import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import {getHtmlDescription} from "../../utils/getHtmlDescription.ts";
import {BestellWizardSettings} from "../../bestell_wizard/types/BestellWizardSettings.ts";
import {Form} from "react-bootstrap";
import {formatCurrency} from "../../utils/formatCurrency.ts";

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
}

const Step6BCoopShares: React.FC<Step6BCoopSharesProps> = ({
  goToNextStep,
  selectedNumberOfCoopShares,
  setSelectedNumberOfCoopShares,
  minimumNumberOfShares,
  studentStatusEnabled,
  setStudentStatusEnabled,
  settings,
}) => {
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
            <h1 className={"text-center"}>{settings.strings.step6bTitle}</h1>
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
            <div className={"d-flex flex-row align-items-center gap-2"}>
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
              />
              <Form.Group style={{ maxWidth: "65px" }}>
                <Form.Control
                  type={"number"}
                  min={minimumNumberOfShares}
                  step={1}
                  value={selectedNumberOfCoopShares}
                  onChange={(event) =>
                    setSelectedNumberOfCoopShares(parseInt(event.target.value))
                  }
                  disabled={studentStatusEnabled}
                />
              </Form.Group>
              <TapirButton
                icon={"add"}
                variant={"outline-secondary"}
                onClick={() => {
                  setSelectedNumberOfCoopShares(selectedNumberOfCoopShares + 1);
                }}
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
            </div>
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
                <Form.Text>
                  Die Immatrikulationsbescheinigung muss per Mail an{" "}
                  <a href={"mailto:" + settings.contactMailAddress}>
                    {settings.contactMailAddress}
                  </a>{" "}
                  gesendet werden.
                </Form.Text>
              </div>
            )}
          </div>
        </div>
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
            icon={"keyboard_arrow_down"}
          />
        </div>
      </div>
    </>
  );
};

export default Step6BCoopShares;
