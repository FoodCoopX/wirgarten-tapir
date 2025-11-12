import React from "react";
import { FloatingLabel, Form } from "react-bootstrap";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";

interface PersonalDataFormControlProps {
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  field: keyof PersonalData;
  placeholder: string;
  type: string;
}

const PersonalDataFormControl: React.FC<PersonalDataFormControlProps> = ({
  personalData,
  setPersonalData,
  field,
  placeholder,
  type,
}) => {
  return (
    <FloatingLabel label={placeholder} controlId={field}>
      <Form.Control
        placeholder={placeholder}
        value={personalData[field]}
        onChange={(event) => {
          personalData[field] = event.target.value;
          setPersonalData(Object.assign({}, personalData));
        }}
        size={"sm"}
        type={type}
      />
    </FloatingLabel>
  );
};

export default PersonalDataFormControl;
