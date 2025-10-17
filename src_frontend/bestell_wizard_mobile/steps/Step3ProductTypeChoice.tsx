import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Form } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

interface Step3ProductTypeChoiceProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  firstName: string;
}

const Step3ProductTypeChoice: React.FC<Step3ProductTypeChoiceProps> = ({
  settings,
  goToNextStep,
  firstName,
}) => {
  return (
    <div
      style={{ height: "100%" }}
      className={
        "d-flex align-items-center justify-content-center gap-2 flex-column text-center"
      }
    >
      <h1>{firstName}, an welchen Anteile hast du Interesse?</h1>
      {settings.productTypes.map((productType) => (
        <Form.Check key={productType.id} label={productType.name} />
      ))}
      <Form.Check label={"Fördermitgliedschaft"} />
      <TapirButton
        variant={"outline-secondary"}
        text={"Weiter"}
        onClick={goToNextStep}
      />
    </div>
  );
};

export default Step3ProductTypeChoice;
