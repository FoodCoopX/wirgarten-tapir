import { useEffect, useState } from "react";
import { Alert, Form } from "react-bootstrap";
import { AssociationDepositPaymentOptionEnum } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { isValidDepositAmount } from "../../utils/isValidDepositAmount.ts";
import NextStepButton from "../components/NextStepButton.tsx";

interface Props {
  settings: BestellWizardSettings;
  required: boolean;
  amount: number | null;
  paymentOption: AssociationDepositPaymentOptionEnum;
  setPaymentOption: (option: AssociationDepositPaymentOptionEnum) => void;
  setAmount: (amount: number | null) => void;
  stepActive: boolean;
  goToNextStep: () => void;
}

export default function Step6DAssociationDeposit({
  settings,
  required,
  amount,
  paymentOption,
  setPaymentOption,
  setAmount,
  stepActive,
  goToNextStep,
}: Readonly<Props>) {
  const deposit = settings.associationDeposit;
  const [value, setValue] = useState(String(amount ?? deposit.minimum));
  const [selected, setSelected] = useState(required || amount !== null);
  const [showError, setShowError] = useState(false);
  const [option, setOption] = useState(paymentOption);
  useEffect(() => {
    if (stepActive) {
      setValue(String(amount ?? deposit.minimum));
      setSelected(required || amount !== null);
      setShowError(false);
      setOption(paymentOption);
    }
  }, [stepActive, required, amount, paymentOption, deposit.minimum]);

  function next() {
    if (option === AssociationDepositPaymentOptionEnum.IndividualAgreement) {
      setAmount(null);
      setPaymentOption(option);
      goToNextStep();
      return;
    }
    if (!required && !selected) {
      setAmount(null);
      setPaymentOption(AssociationDepositPaymentOptionEnum.Once);
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
    setPaymentOption(option);
    goToNextStep();
  }

  return (
    <>
      <p>
        {deposit.name}: Der rückzahlbare Betrag wird pro Mitglied vereinbart und
        einmalig per SEPA-Lastschrift eingezogen. Vereinsmitgliedschaft,
        Vereinsbeitrag und laufende Ernte-/Solidarbeiträge bestehen unabhängig
        davon.
      </p>
      {!required &&
        option !== AssociationDepositPaymentOptionEnum.IndividualAgreement && (
          <Form.Check
            id="voluntary-deposit"
            label="Ich möchte freiwillig einen Einlagenbetrag leisten."
            checked={selected}
            onChange={(event) => {
              setSelected(event.target.checked);
              if (!event.target.checked)
                setOption(AssociationDepositPaymentOptionEnum.Once);
            }}
          />
        )}
      {(required || selected) &&
        option !== AssociationDepositPaymentOptionEnum.IndividualAgreement && (
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
      {deposit.allowSignupWithoutDeposit && (
        <Form.Check
          className="mt-3"
          id="deposit-individual-agreement-request"
          label={deposit.signupWithoutDepositLabel}
          checked={
            option === AssociationDepositPaymentOptionEnum.IndividualAgreement
          }
          onChange={(event) => {
            setOption(
              event.target.checked
                ? AssociationDepositPaymentOptionEnum.IndividualAgreement
                : AssociationDepositPaymentOptionEnum.Once,
            );
            setShowError(false);
          }}
        />
      )}
      {option === AssociationDepositPaymentOptionEnum.IndividualAgreement && (
        <Alert variant="info" className="mt-3">
          Du kannst die Anmeldung abschließen. Die Verwaltung klärt die Einlage
          mit dir. Bis dahin wird keine Einlage eingezogen.
        </Alert>
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
