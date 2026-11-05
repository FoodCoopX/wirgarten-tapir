import { useState } from "react";
import { Alert, Form } from "react-bootstrap";
import { DepositConfiguration } from "../../api-client";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import NextStepButton from "../components/NextStepButton.tsx";

export default function StepAssociationDeposit({
  configuration,
  amount,
  setAmount,
  hardship,
  setHardship,
  optional,
  instalments,
  setInstalments,
  goToNextStep,
  stepActive,
}: {
  configuration: DepositConfiguration;
  amount: string;
  setAmount: (value: string) => void;
  hardship: boolean;
  setHardship: (value: boolean) => void;
  optional: boolean;
  instalments: boolean;
  setInstalments: (value: boolean) => void;
  goToNextStep: () => void;
  stepActive: boolean;
}) {
  const [error, setError] = useState("");
  const minimum = Number(configuration.minimum);
  const increment = Number(configuration.increment);
  function next() {
    const value = Number(amount);
    const cents = Math.round(value * 100);
    if (
      !hardship &&
      !(optional && value === 0) &&
      (!Number.isFinite(value) ||
        value < minimum ||
        Math.abs(value * 100 - cents) > 0.000001 ||
        (cents - Math.round(minimum * 100)) % Math.round(increment * 100) !== 0)
    ) {
      setError(
        `Bitte mindestens ${formatCurrency(minimum)} in Schritten von ${formatCurrency(increment)} eingeben.`,
      );
      return;
    }
    setError("");
    goToNextStep();
  }
  return (
    <>
      <p>
        Die rückzahlbare Einlage wird einmalig pro Mitglied geleistet. Sie kommt
        zu Vereins- und Erntebeiträgen hinzu.
      </p>
      {optional && (
        <Form.Check
          type="checkbox"
          id="deposit-optional"
          label="Als Fördermitglied keine Einlage leisten"
          checked={amount === "0" && !hardship}
          onChange={(event) => {
            setHardship(false);
            setAmount(event.target.checked ? "0" : configuration.minimum);
          }}
        />
      )}
      <Form.Group controlId="association-deposit-amount">
        <Form.Label>{configuration.name} (€)</Form.Label>
        <Form.Control
          type="number"
          min={minimum}
          step={increment}
          value={hardship ? "" : amount}
          disabled={
            hardship ||
            !configuration.allowExtraSignup ||
            (optional && amount === "0")
          }
          onChange={(event) => setAmount(event.target.value)}
        />
        <Form.Text>
          Mindestbetrag: {formatCurrency(minimum)}. Schrittgröße:{" "}
          {formatCurrency(increment)}.
        </Form.Text>
      </Form.Group>
      {configuration.instalmentsEnabled && !hardship && Number(amount) > 0 && (
        <Form.Check
          type="checkbox"
          id="deposit-instalments"
          className="mt-3"
          checked={instalments}
          onChange={(event) => setInstalments(event.target.checked)}
          label={`Einlage in ${configuration.instalmentCount} monatlichen Raten zahlen (insgesamt ${formatCurrency(Number(amount))})`}
        />
      )}
      {configuration.allowHardship && (
        <>
          <Form.Check
            type="checkbox"
            id="deposit-hardship"
            className="mt-3"
            label={configuration.hardshipLabel}
            checked={hardship}
            onChange={(event) => {
              setHardship(event.target.checked);
              setError("");
              if (!event.target.checked) setAmount(configuration.minimum);
            }}
          />
          {hardship && (
            <Alert variant="info">{configuration.hardshipText}</Alert>
          )}
        </>
      )}
      {error && <Alert variant="danger">{error}</Alert>}
      <NextStepButton
        onClick={next}
        isOrderStep={false}
        stepActive={stepActive}
      />
    </>
  );
}
