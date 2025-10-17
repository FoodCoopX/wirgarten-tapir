import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Form } from "react-bootstrap";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";

interface Step2FirstNameProps {
  goToNextStep: () => void;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
}

const Step2FirstName: React.FC<Step2FirstNameProps> = ({
  goToNextStep,
  personalData,
  setPersonalData,
}) => {
  return (
    <div
      style={{ height: "100%" }}
      className={
        "d-flex align-items-center justify-content-center gap-2 flex-column text-center"
      }
    >
      <h1>Los geht's: Wie heißt du?</h1>
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
      />
    </div>
  );
};

export default Step2FirstName;
