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

  useEffect(() => {
    if (selectedValue !== "custom") {
      setSolidarityContribution(selectedValue);
      return;
    }
    const customContribution = parseFloat(customValue.replace("\u00A0€", ""));
    if (isNaN(customContribution)) {
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

    if (
      showMinimumWarning() ||
      getMonthlyPayment(
        solidarityContribution,
        shoppingCart,
        settings,
        productTypesInWaitingList,
      ) < 0
    ) {
      return;
    }

    goToNextStep();
  }

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
          isValid={
            showValidation &&
            !showMinimumWarning() &&
            getMonthlyPayment(
              solidarityContribution,
              shoppingCart,
              settings,
              productTypesInWaitingList,
            ) > 0
          }
          isInvalid={
            showValidation &&
            (showMinimumWarning() ||
              getMonthlyPayment(
                solidarityContribution,
                shoppingCart,
                settings,
                productTypesInWaitingList,
              ) < 0)
          }
        >
          {getValues().map((value) => (
            <option key={value} value={value}>
              {getDisplay(value)}
            </option>
          ))}
        </Form.Select>
        {selectedValue === "custom" && (
          <Form.Group className={"d-flex flex-column gap-2 align-items-center"}>
            {settings.solidarityContributionUnit === "percentage" && (
              <Form.Text>
                Bitte ein Prozentzahl eingeben. Beispiel: '5' eingeben um 5%
                extra beizutragen.
              </Form.Text>
            )}
            {settings.solidarityContributionUnit === "absolute" && (
              <Form.Text>
                Bitte ein Zahl eingeben. Beispiel: '5' eingeben um 5€ extra
                beizutragen, oder '-10' um 10€ weniger zu zahlen.
              </Form.Text>
            )}
            <Form.Control
              id={"custom_solidarity_contribution"}
              placeholder={"Personalisierter Beitrag"}
              value={customValue}
              onChange={(event) =>
                setCustomValue(
                  event.target.value
                    .replace("\u00A0", "")
                    .replace("€", "")
                    .trim() + "\u00A0€",
                )
              }
              style={{ maxWidth: "300px" }}
              isValid={
                showValidation &&
                !showMinimumWarning() &&
                getMonthlyPayment(
                  solidarityContribution,
                  shoppingCart,
                  settings,
                  productTypesInWaitingList,
                ) > 0
              }
              isInvalid={
                showValidation &&
                (showMinimumWarning() ||
                  getMonthlyPayment(
                    solidarityContribution,
                    shoppingCart,
                    settings,
                    productTypesInWaitingList,
                  ) < 0)
              }
            />
            {showMinimumWarning() && (
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
