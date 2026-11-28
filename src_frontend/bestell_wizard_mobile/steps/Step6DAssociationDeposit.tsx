import React, { useEffect, useState } from "react";
import { Alert, Form } from "react-bootstrap";
import { AssociationDepositPaymentOptionEnum } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { isValidDepositAmount } from "../../utils/isValidDepositAmount.ts";
import NextStepButton from "../components/NextStepButton.tsx";

interface Step6DAssociationDepositProps {
  settings: BestellWizardSettings;
  amount: number | null;
  paymentOption: AssociationDepositPaymentOptionEnum;
  setPaymentOption: (option: AssociationDepositPaymentOptionEnum) => void;
  setAmount: (amount: number | null) => void;
  stepActive: boolean;
  goToNextStep: () => void;
}

const Step6DAssociationDeposit: React.FC<
  Readonly<Step6DAssociationDepositProps>
> = ({
  settings,
  amount,
  paymentOption,
  setPaymentOption,
  setAmount,
  stepActive,
  goToNextStep,
}) => {
  const depositSettings = settings.associationDeposit;
  const [value, setValue] = useState(String(amount || depositSettings.minimum));
  const [showError, setShowError] = useState(false);
  const [option, setOption] = useState(paymentOption);
  useEffect(() => {
    if (stepActive) {
      setValue(String(amount || depositSettings.minimum));
      setShowError(false);
      setOption(paymentOption);
    }
  }, [stepActive, amount, paymentOption, depositSettings.minimum]);

  function onNextClicked() {
    if (option === AssociationDepositPaymentOptionEnum.IndividualAgreement) {
      setAmount(0);
      setPaymentOption(option);
      goToNextStep();
      return;
    }
    const parsed = Number(value);
    if (
      !value ||
      !isValidDepositAmount(
        parsed,
        depositSettings.minimum,
        depositSettings.increment,
      ) ||
      (!depositSettings.allowLargerSignup && parsed !== depositSettings.minimum)
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
        {depositSettings.name}: {depositSettings.signupText}
      </p>
      {option !== AssociationDepositPaymentOptionEnum.IndividualAgreement && (
        <Form.Group controlId="signup-depositSettings-amount">
          <Form.Label>{depositSettings.name} (€)</Form.Label>
          <Form.Control
            type="number"
            min={depositSettings.minimum}
            step={depositSettings.increment}
            value={value}
            disabled={!depositSettings.allowLargerSignup}
            onChange={(event) => setValue(event.target.value)}
            isInvalid={showError}
          />
          <Form.Text>
            Mindestens {formatCurrency(depositSettings.minimum)}
            {depositSettings.allowLargerSignup &&
              `; weitere Schritte von ${formatCurrency(depositSettings.increment)}`}
            .
          </Form.Text>
        </Form.Group>
      )}
      {depositSettings.allowSignupWithoutDeposit && (
        <Form.Check
          className="mt-3"
          id="depositSettings-individual-agreement-request"
          label={depositSettings.signupWithoutDepositLabel}
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
      {showError && (
        <Alert variant="danger">
          Bitte einen gültigen Betrag in den angegebenen Schritten wählen.
        </Alert>
      )}
      <NextStepButton onClick={onNextClicked} stepActive={stepActive} />
    </>
  );
};

export default Step6DAssociationDeposit;
