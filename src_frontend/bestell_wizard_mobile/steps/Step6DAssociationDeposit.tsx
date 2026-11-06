import { useEffect, useState } from "react";
import { Alert, Form } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { isValidDepositAmount } from "../../utils/isValidDepositAmount.ts";
import NextStepButton from "../components/NextStepButton.tsx";

interface Props {
  settings: BestellWizardSettings;
  required: boolean;
  amount: number | null;
  setAmount: (amount: number | null) => void;
  stepActive: boolean;
  goToNextStep: () => void;
}

export default function Step6DAssociationDeposit({
  settings,
  required,
  amount,
  setAmount,
  stepActive,
  goToNextStep,
}: Readonly<Props>) {
  const deposit = settings.associationDeposit;
  const [value, setValue] = useState(String(amount ?? deposit.minimum));
  const [selected, setSelected] = useState(required || amount !== null);
  const [showError, setShowError] = useState(false);
  useEffect(() => {
    if (stepActive) {
      setValue(String(amount ?? deposit.minimum));
      setSelected(required || amount !== null);
      setShowError(false);
    }
  }, [stepActive]);

  function next() {
    if (!required && !selected) {
      setAmount(null);
      goToNextStep();
      return;
    }
    const parsed = Number(value);
    if (
      !value ||
      !isValidDepositAmount(parsed, deposit.minimum, deposit.increment) ||
      (!deposit.allowLargerSignup && parsed !== deposit.minimum)
    ) {
      setShowError(true);
      return;
    }
    setAmount(parsed);
    goToNextStep();
  }

  return (
    <>
      <p>
        Die rückzahlbare {deposit.name} wird einmalig pro Mitglied über das
        SEPA-Mandat eingezogen. Vereinsmitgliedschaft, Vereinsbeitrag und
        laufende Ernte-/Solidarbeiträge bestehen unabhängig davon.
      </p>
      {!required && (
        <Form.Check
          id="voluntary-deposit"
          label={`Ich möchte freiwillig eine ${deposit.name} leisten.`}
          checked={selected}
          onChange={(event) => setSelected(event.target.checked)}
        />
      )}
      {(required || selected) && (
        <Form.Group controlId="signup-deposit-amount">
          <Form.Label>{deposit.name} (€)</Form.Label>
          <Form.Control
            type="number"
            min={deposit.minimum}
            step={deposit.increment}
            value={value}
            disabled={!deposit.allowLargerSignup}
            onChange={(event) => setValue(event.target.value)}
            isInvalid={showError}
          />
          <Form.Text>
            Mindestens {formatCurrency(deposit.minimum)}
            {deposit.allowLargerSignup &&
              `; weitere Schritte von ${formatCurrency(deposit.increment)}`}
            .
          </Form.Text>
        </Form.Group>
      )}
      {showError && (
        <Alert variant="danger">
          Bitte einen gültigen Betrag in den angegebenen Schritten wählen.
        </Alert>
      )}
      <NextStepButton onClick={next} stepActive={stepActive} />
    </>
  );
}
