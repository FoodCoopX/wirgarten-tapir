import React, { CSSProperties } from "react";
import { FloatingLabel, Form } from "react-bootstrap";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";

interface PersonalDataFormControlProps {
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  field: keyof PersonalData;
  placeholder: string;
  type: string;
  showValidation: boolean;
  isValid: boolean;
  extraText?: string;
  style?: CSSProperties;
}

const PersonalDataFormControl: React.FC<PersonalDataFormControlProps> = ({
  personalData,
  setPersonalData,
  field,
  placeholder,
  type,
  showValidation,
  isValid,
  extraText,
  style,
}) => {
  return (
    <div style={style} className={"d-flex flex-column"}>
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
          isValid={showValidation && isValid}
          isInvalid={showValidation && !isValid}
        />
      </FloatingLabel>
      {extraText && (
        <Form.Text className={showValidation && !isValid ? "text-danger" : ""}>
          {extraText}
        </Form.Text>
      )}
    </div>
  );
};

export default PersonalDataFormControl;
