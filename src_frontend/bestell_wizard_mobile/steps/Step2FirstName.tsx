import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Form } from "react-bootstrap";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

interface Step2FirstNameProps {
  goToNextStep: () => void;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  settings: BestellWizardSettings;
}

const Step2FirstName: React.FC<Step2FirstNameProps> = ({
  goToNextStep,
  personalData,
  setPersonalData,
  settings,
}) => {
  return (
    <div
      style={{ height: "100%" }}
      className={
        "d-flex align-items-center justify-content-center gap-2 flex-column text-center"
      }
    >
      {settings.strings.step2Title && <h1>{settings.strings.step2Title}</h1>}
      {settings.strings.step2Text && <p>{settings.strings.step2Text}</p>}
      <Form.Control
        placeholder={"Vorname"}
        style={{ maxWidth: "300px" }}
        value={personalData.firstName}
        onChange={(event) => {
          personalData.firstName = event.target.value;
          setPersonalData(Object.assign({}, personalData));
        }}
      />
      <TapirButton
        variant={"outline-secondary"}
        text={"Weiter"}
        onClick={goToNextStep}
        disabled={personalData.firstName.length === 0}
      />
    </div>
  );
};

export default Step2FirstName;
