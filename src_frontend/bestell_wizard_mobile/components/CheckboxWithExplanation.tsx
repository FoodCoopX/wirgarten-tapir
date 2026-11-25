import React from "react";
import { Accordion } from "react-bootstrap";
import { scrollIntoView } from "../utils/scrollIntoView.ts";
import TapirCheckbox from "./TapirCheckbox.tsx";

interface CheckboxWithExplanationProps {
  controlId: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  explanation: string;
  showError?: boolean;
}

const CheckboxWithExplanation: React.FC<CheckboxWithExplanationProps> = ({
  controlId,
  checked,
  onChange,
  label,
  explanation,
  showError,
}) => {
  const checkbox = (
    <TapirCheckbox
      controlId={controlId}
      checked={checked}
      onChange={onChange}
      label={label}
      showError={showError}
    />
  );

  if (explanation.trim().length === 0) {
    return checkbox;
  }

  return (
    <Accordion style={{ width: "100%" }}>
      <Accordion.Item eventKey={controlId} onClick={scrollIntoView}>
        <Accordion.Header>{checkbox}</Accordion.Header>
        <Accordion.Body>
          <span dangerouslySetInnerHTML={{ __html: explanation }} />
        </Accordion.Body>
      </Accordion.Item>
    </Accordion>
  );
};

export default CheckboxWithExplanation;
