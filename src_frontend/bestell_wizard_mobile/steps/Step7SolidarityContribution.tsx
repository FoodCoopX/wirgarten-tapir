import React, { useEffect, useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { Alert, Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { getMonthlyPayment } from "../utils/getMonthlyPayment.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";

interface Step7SolidarityContributionProps {
  goToNextStep: () => void;
  settings: BestellWizardSettings;
  solidarityContribution: number;
  setSolidarityContribution: (c: number) => void;
  active: boolean;
  shoppingCart: ShoppingCart;
  productTypesInWaitingList: Set<PublicProductType>;
}

const SUFFIX = "\u00A0€";

const Step7SolidarityContribution: React.FC<
  Step7SolidarityContributionProps
> = ({
  goToNextStep,
  settings,
  setSolidarityContribution,
  active,
  solidarityContribution,
  shoppingCart,
  productTypesInWaitingList,
}) => {
  const [selectedValue, setSelectedValue] = useState<number | "custom">(0);
  const [customValue, setCustomValue] = useState("");
  const [showValidation, setShowValidation] = useState(false);
  const [defaultValueSet, setDefaultValueSet] = useState(false);

  useEffect(() => {
    if (defaultValueSet) {
      return;
    }
    setDefaultValueSet(true);

    if (getValues().includes(settings.solidarityContributionDefault)) {
      setSelectedValue(settings.solidarityContributionDefault);
    } else {
      setSelectedValue("custom");
      setCustomValue(settings.solidarityContributionDefault + SUFFIX);
    }
  }, [settings]);

  useEffect(() => {
    if (selectedValue !== "custom") {
      setSolidarityContribution(selectedValue);
      return;
    }
    const customContribution = Number.parseFloat(
      customValue.replace(SUFFIX, ""),
    );
    if (Number.isNaN(customContribution)) {
      return;
    }
    setSolidarityContribution(customContribution);
  }, [selectedValue, customValue]);

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

  function validate() {
    setShowValidation(true);

    if (!isValueValid(solidarityContribution)) {
      return;
    }

    goToNextStep();
  }

  function getValues(): (number | "custom")[] {
    return settings.solidarityContributionChoices.map((choiceAsString) =>
      choiceAsString === "custom"
        ? "custom"
        : Number.parseFloat(choiceAsString),
    );
  }

  function getDisplay(value: number | "custom") {
    if (value === "custom") {
      return "Ich möchte einen anderen Betrag zahlen";
    }
    return formatCurrency(value);
  }

  function onSelect(selected: string) {
    if (selected === "custom") {
      setSelectedValue(selected);
    } else {
      setSelectedValue(Number.parseFloat(selected));
    }
  }

  function isValueValid(value: number) {
    if (
      getMonthlyPayment(
        value,
        shoppingCart,
        settings,
        productTypesInWaitingList,
      ) < 0
    ) {
      return false;
    }

    if (settings.solidarityContributionMinimum === null) {
      return true;
    }

    return value >= settings.solidarityContributionMinimum;
  }

  function updateCustomValue(inputValue: string) {
    const cleanedValue = inputValue
      .replace("\u00A0", "")
      .replace("€", "")
      .trim();

    const floatValue = Number.parseFloat(cleanedValue);
    if (Number.isNaN(floatValue)) {
      setCustomValue(cleanedValue);
      return;
    }

    setCustomValue(formatCurrency(Number.parseFloat(cleanedValue)));
    const input = document.getElementById(
      "custom_solidarity_contribution",
    ) as HTMLInputElement;
    const selectionStart = input.selectionStart;
    setTimeout(() => {
      input.selectionStart = selectionStart;
      input.selectionEnd = selectionStart;
    }, 10);
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
          isValid={showValidation && isValueValid(solidarityContribution)}
          isInvalid={showValidation && !isValueValid(solidarityContribution)}
        >
          {getValues()
            .filter((value) => value === "custom" || isValueValid(value))
            .map((value) => (
              <option key={value} value={value}>
                {getDisplay(value)}
              </option>
            ))}
        </Form.Select>
        {selectedValue === "custom" && (
          <Form.Group className={"d-flex flex-column gap-2 align-items-center"}>
            <Form.Text>
              Bitte eine Zahl eingeben. Beispiel: '5' eingeben um 5€ extra
              beizutragen, oder '-10' um 10€ weniger zu zahlen.
            </Form.Text>
            <Form.Control
              id={"custom_solidarity_contribution"}
              placeholder={"Personalisierter Beitrag"}
              value={customValue}
              onChange={(event) => updateCustomValue(event.target.value)}
              style={{ maxWidth: "300px" }}
              isValid={showValidation && isValueValid(solidarityContribution)}
              isInvalid={
                showValidation && !isValueValid(solidarityContribution)
              }
            />
            {!isValueValid(solidarityContribution) &&
              (settings.solidarityContributionMinimum ?? 0) < 0 && (
                <Alert variant={"danger"}>
                  Der Solidartopf reicht gerade nur für{" "}
                  {formatCurrency(settings.solidarityContributionMinimum ?? 0)}
                </Alert>
              )}
          </Form.Group>
        )}
      </div>
      <NextStepButton onClick={validate} />
    </div>
  );
};

export default Step7SolidarityContribution;
