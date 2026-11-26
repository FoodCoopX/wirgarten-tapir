import "@eonasdan/tempus-dominus/dist/css/tempus-dominus.min.css";
import "@fortawesome/fontawesome-free/css/fontawesome.css";
import "@fortawesome/fontawesome-free/css/solid.css";
import React from "react";
import { Alert, Form } from "react-bootstrap";
import DateTimePicker from "./dateTimePicker";

interface FormGroupProps {
  label: string;
  type: string;
  value: any;
  additionalData?: any;
  onChange: (newValue: any) => void;
}

const TapirMailFormGroup: React.FC<FormGroupProps> = ({
  label,
  type,
  value,
  additionalData = {},
  onChange,
}) => {
  function renderInput() {
    switch (type) {
      case "datetime":
        return (
          <DateTimePicker
            initialValue={value ? new Date(value) : new Date(Date.now())}
            onChange={onChange}
          />
        );
      case "checkbox":
        return <Form.Check onChange={onChange} defaultChecked={value} />;
      case "dropdown":
        if (!additionalData.choices || additionalData.choices.length === 0) {
          return (
            <Alert variant="warning">Trigger ist nicht konfiguriert</Alert>
          );
        }
        return (
          <Form.Control
            as="select"
            onChange={(e) => onChange(e.target.value)}
            defaultValue={value}
          >
            {additionalData.choices.map((choice: any) => (
              <option key={choice.value} value={choice.value}>
                {choice.label}
              </option>
            ))}
          </Form.Control>
        );

      default:
        return (
          <Form.Control
            required={true}
            type={type}
            defaultValue={value}
            onChange={(e) => {
              onChange(e.target.value);
            }}
          />
        );
    }
  }

  return (
    <Form.Group style={{ marginBottom: "1em" }}>
      <Form.Label>{label}</Form.Label>
      {renderInput()}
    </Form.Group>
  );
};

export default TapirMailFormGroup;
