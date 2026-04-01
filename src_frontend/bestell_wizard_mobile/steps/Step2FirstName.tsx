import React, { useEffect, useState } from "react";
import { Form } from "react-bootstrap";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";

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
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (active) {
      setTimeout(
        () => document.getElementById("first_name_input")?.focus(),
        200,
      );
    } else {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

  function validate() {
    setShowValidation(true);
    if (personalData.firstName.length > 0) {
      goToNextStep();
    }
  }

  return (
    <>
      {settings.strings.step2Text && <p>{settings.strings.step2Text}</p>}
      <Form.Control
        placeholder={"Vorname"}
        style={{ maxWidth: "300px" }}
        value={personalData.firstName}
        onChange={(event) => {
          personalData.firstName = event.target.value;
          setPersonalData({ ...personalData });
        }}
        id={"first_name_input"}
        onKeyUp={(event) => {
          if (event.key === "Enter") validate();
        }}
        isValid={showValidation && personalData.firstName.length > 0}
        isInvalid={showValidation && personalData.firstName.length === 0}
      />
      <NextStepButton onClick={validate} />
    </>
  );
};

export default Step2FirstName;
