import React, { useEffect } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Form } from "react-bootstrap";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import StepTitle from "../components/StepTitle.tsx";

interface Step2FirstNameProps {
  goToNextStep: () => void;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  settings: BestellWizardSettings;
  active: boolean;
}

const Step2FirstName: React.FC<Step2FirstNameProps> = ({
  goToNextStep,
  personalData,
  setPersonalData,
  settings,
  active,
}) => {
  useEffect(() => {
    if (!active) return;

    setTimeout(() => document.getElementById("first_name_input")?.focus(), 200);
  }, [active]);

  return (
    <div
      style={{ height: "100%" }}
      className={
        "d-flex align-items-center justify-content-center gap-2 flex-column text-center"
      }
    >
      {settings.strings.step2Title && (
        <StepTitle title={settings.strings.step1aTitle} />
      )}
      {settings.strings.step2Text && <p>{settings.strings.step2Text}</p>}
      <Form.Control
        placeholder={"Vorname"}
        style={{ maxWidth: "300px" }}
        value={personalData.firstName}
        onChange={(event) => {
          personalData.firstName = event.target.value;
          setPersonalData(Object.assign({}, personalData));
        }}
        id={"first_name_input"}
        onKeyUp={(event) => {
          if (event.key === "Enter") goToNextStep();
        }}
      />
      <TapirButton
        variant={"outline-secondary"}
        text={"Weiter"}
        onClick={goToNextStep}
        disabled={personalData.firstName.length === 0}
        icon={"keyboard_arrow_down"}
        size={"sm"}
      />
    </div>
  );
};

export default Step2FirstName;
