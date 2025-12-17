import React, { useEffect, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import TapirCheckbox from "../components/TapirCheckbox.tsx";
import "../utils/flexColOnSmallScreen.css";

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
  active: boolean;
  isOrderStep: boolean;
  orderLoading: boolean;
  nextButtonText?: string;
}

const Step6BCoopShares: React.FC<Step6BCoopSharesProps> = ({
  goToNextStep,
  selectedNumberOfCoopShares,
  setSelectedNumberOfCoopShares,
  minimumNumberOfShares,
  studentStatusEnabled,
  setStudentStatusEnabled,
  settings,
  statuteAccepted,
  setStatuteAccepted,
  active,
  isOrderStep,
  orderLoading,
  nextButtonText,
}) => {
  const [statuteRead, setStatuteRead] = useState(false);
  const [commitmentChecked, setCommitmentChecked] = useState(false);
  const [internalNumberOfShares, setInternalNumberOfShares] = useState("");
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

  useEffect(() => {
    if (statuteAccepted !== (statuteRead && commitmentChecked)) {
      setStatuteAccepted(statuteRead && commitmentChecked);
    }
  }, [statuteRead, commitmentChecked]);

  useEffect(() => {
    if (statuteAccepted) {
      setStatuteRead(statuteAccepted);
      setCommitmentChecked(statuteAccepted);
    }
  }, [statuteAccepted]);

  function validate() {
    setShowValidation(true);
    if (canGoToNextStep()) {
      goToNextStep();
    }
  }

  function canGoToNextStep() {
    if (studentStatusEnabled) {
      return true;
    }

    if (!statuteRead || !commitmentChecked) {
      return false;
    }

    return selectedNumberOfCoopShares >= minimumNumberOfShares;
  }

  useEffect(() => {
    if (
      Number.isNaN(Number.parseInt(internalNumberOfShares)) ||
      Number.parseInt(internalNumberOfShares) < minimumNumberOfShares
    ) {
      setInternalNumberOfShares(minimumNumberOfShares.toString());
    }
  }, [minimumNumberOfShares]);

  useEffect(() => {
    const newNumberOfShares = Number.parseInt(internalNumberOfShares);
    if (Number.isNaN(newNumberOfShares)) {
      return;
    }

    if (newNumberOfShares !== selectedNumberOfCoopShares) {
      setSelectedNumberOfCoopShares(newNumberOfShares);
    }
  }, [internalNumberOfShares]);

  return (
    <>
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
          variant={BUTTON_VARIANT}
          onClick={() => {
            setInternalNumberOfShares(
              Math.max(
                minimumNumberOfShares,
                selectedNumberOfCoopShares - 1,
              ).toString(),
            );
          }}
          disabled={
            studentStatusEnabled ||
            selectedNumberOfCoopShares <= minimumNumberOfShares
          }
          size={"sm"}
        />
        <Form.Group style={{ maxWidth: showValidation ? "60px" : "35px" }}>
          <Form.Control
            min={minimumNumberOfShares}
            step={1}
            value={studentStatusEnabled ? 0 : internalNumberOfShares}
            onChange={(event) => setInternalNumberOfShares(event.target.value)}
            size={"sm"}
            disabled={studentStatusEnabled}
            isValid={
              showValidation &&
              selectedNumberOfCoopShares >= minimumNumberOfShares
            }
            isInvalid={
              showValidation &&
              selectedNumberOfCoopShares < minimumNumberOfShares
            }
          />
        </Form.Group>
        <TapirButton
          icon={"add"}
          variant={BUTTON_VARIANT}
          onClick={() => {
            setInternalNumberOfShares(
              (selectedNumberOfCoopShares + 1).toString(),
            );
          }}
          size={"sm"}
          disabled={studentStatusEnabled}
        />
        <span>
          {" × "}
          {formatCurrency(settings.priceOfAShare)} ={" "}
        </span>
        <span>
          <strong>
            {formatCurrency(
              studentStatusEnabled
                ? 0
                : selectedNumberOfCoopShares * settings.priceOfAShare,
            )}
          </strong>
        </span>
      </small>
      <div className={"d-flex flex-column gap-2 mx-4"}>
        {settings.studentStatusAllowed && (
          <>
            <TapirCheckbox
              checked={studentStatusEnabled}
              onChange={(checked) => {
                setStudentStatusEnabled(checked);
                setSelectedNumberOfCoopShares(
                  checked ? 0 : minimumNumberOfShares,
                );
              }}
              label={
                "Ich bin Student*in und kann keine Genossenschaftsanteile zeichnen"
              }
              controlId={"studentStatus"}
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
          </>
        )}
        <TapirCheckbox
          controlId={"statuteRead"}
          checked={statuteRead && !studentStatusEnabled}
          onChange={setStatuteRead}
          label={settings.strings.step6cCheckboxStatute}
          disabled={studentStatusEnabled}
          showError={showValidation && !studentStatusEnabled && !statuteRead}
        />
        <TapirCheckbox
          controlId={"commitment"}
          checked={commitmentChecked && !studentStatusEnabled}
          onChange={(checked) => setCommitmentChecked(checked)}
          label={settings.strings.step6cCheckboxCommitment}
          disabled={studentStatusEnabled}
          showError={
            showValidation && !studentStatusEnabled && !commitmentChecked
          }
        />
      </div>
      <NextStepButton
        onClick={validate}
        loading={orderLoading}
        isOrderStep={isOrderStep}
        text={nextButtonText}
      />
    </>
  );
};

export default Step6BCoopShares;
