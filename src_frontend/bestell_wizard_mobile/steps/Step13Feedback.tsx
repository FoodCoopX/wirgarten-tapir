import React, { useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Form } from "react-bootstrap";
import NextStepButton from "../components/NextStepButton.tsx";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";

interface Step13FeedbackProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
}

const Step13Feedback: React.FC<Step13FeedbackProps> = ({
  settings,
  goToNextStep,
}) => {
  const [feedback, setFeedback] = useState("");

  return (
    <>
      <p
        className={"text-center"}
        dangerouslySetInnerHTML={getHtmlDescription(
          settings.strings.step13Text +
            "<br />Ist gerade nur als Platzhalder da, der Auswahl wird nicht gespeichert",
        )}
      />
      <Form.Group style={{ width: "100%" }}>
        <Form.Control
          as={"textarea"}
          onChange={(event) => setFeedback(event.target.value)}
          placeholder={"Dein Feedback"}
        />
      </Form.Group>
      <NextStepButton onClick={goToNextStep} text={"Bestellung bestätigen"} />
    </>
  );
};

export default Step13Feedback;
