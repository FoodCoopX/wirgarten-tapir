import React, { useState } from "react";
import { Button, Collapse } from "react-bootstrap";

interface CalculationExplanationProps {
  text: string | undefined;
}

const CalculationExplanation: React.FC<CalculationExplanationProps> = ({
  text,
}) => {
  const [open, setOpen] = useState(false);

  if (!text) {
    return null;
  }

  return (
    <div className={"d-flex flex-column align-items-center"}>
      <Button
        variant={"link"}
        size={"sm"}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {open ? "Berechnung ausblenden" : "Berechnung anzeigen"}
      </Button>
      <Collapse in={open}>
        <div>
          <small style={{ whiteSpace: "pre-line" }}>{text}</small>
        </div>
      </Collapse>
    </div>
  );
};

export default CalculationExplanation;
