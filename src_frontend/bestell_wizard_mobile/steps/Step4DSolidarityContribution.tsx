import React, { useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { Alert, Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";

interface Step4DSolidarityContributionProps {
  goToNextStep: () => void;
  settings: BestellWizardSettings;
}

const Step4DSolidarityContribution: React.FC<
  Step4DSolidarityContributionProps
> = ({ goToNextStep, settings }) => {
  const [selectedValue, setSelectedValue] = useState<number | "custom">(0);
  const [customValue, setCustomValue] = useState("");

  function getValues(): (number | "custom")[] {
    return settings.solidarityContributionChoices.map((choiceAsString) =>
      choiceAsString === "custom" ? "custom" : parseFloat(choiceAsString),
    );
  }

  function getDisplay(value: number | "custom") {
    switch (value) {
      case "custom":
        return "Ich möchte einen anderen Betrag zahlen";
      case 0:
        return "Ich möchten den Richtpreis zahlen";
      default:
        switch (settings.solidarityContributionUnit) {
          case "absolute":
            return formatCurrency(value);
          case "percentage":
            return value + "%";
        }
    }
  }

  function onSelect(selected: string) {
    if (selected === "custom") {
      setSelectedValue(selected);
    } else {
      setSelectedValue(parseFloat(selected));
    }
  }

  function showMinimumWarning() {
    if (selectedValue !== "custom") {
      return false;
    }

    if (isNaN(parseFloat(customValue))) {
      return false;
    }

    if (settings.solidarityContributionMinimum === null) {
      return false;
    }

    return parseFloat(customValue) < settings.solidarityContributionMinimum;
  }

  return (
    <div className={"d-flex flex-column gap-2 align-items-center"}>
      {settings.strings.step4dText && (
        <p className={"text-center"}>{settings.strings.step4dText}</p>
      )}
      <div
        className={"d-flex flex-column gap-2 align-items-center"}
        style={{ maxWidth: "500px" }}
      >
        <Form.Select
          value={selectedValue}
          onChange={(event) => onSelect(event.target.value)}
        >
          {getValues().map((value) => (
            <option value={value}>{getDisplay(value)}</option>
          ))}
        </Form.Select>
        {selectedValue === "custom" && (
          <Form.Group>
            <Form.Control
              placeholder={"Personalisierter Beitrag"}
              type={"number"}
              step={0.01}
              min={settings.solidarityContributionMinimum ?? undefined}
              value={customValue}
              onChange={(event) => setCustomValue(event.target.value)}
            />
            {settings.solidarityContributionUnit === "percentage" && (
              <Form.Text>
                Bitte ein Prozentzahl eingeben. Beispiel: '5' eingeben um 5%
                extra beizutragen.
              </Form.Text>
            )}
            {showMinimumWarning() && (
              <Alert variant={"danger"}>
                Der Solidartopf reicht gerade nur für{" "}
                {formatCurrency(settings.solidarityContributionMinimum ?? 0)}
              </Alert>
            )}
          </Form.Group>
        )}
      </div>
      <NextStepButton onClick={goToNextStep} disabled={showMinimumWarning()} />
    </div>
  );
};

export default Step4DSolidarityContribution;
