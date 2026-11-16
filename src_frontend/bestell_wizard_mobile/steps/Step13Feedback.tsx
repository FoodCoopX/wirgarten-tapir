import React from "react";
import { Form } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../../components/mobile_wizard/NextStepButton.tsx";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";

interface Step13FeedbackProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  confirmOrder?: () => void;
  confirmOrderLoading: boolean;
  feedback: string;
  setFeedback: (value: string) => void;
  stepActive: boolean;
  isOrderStep?: boolean;
}

const Step13Feedback: React.FC<Step13FeedbackProps> = ({
  settings,
  goToNextStep,
  confirmOrder,
  confirmOrderLoading,
  feedback,
  setFeedback,
  stepActive,
  isOrderStep = true,
}) => {
  return (
    <>
      <p
        className={"text-center"}
        dangerouslySetInnerHTML={getHtmlDescription(
          settings.strings.step13Text,
        )}
      />
      <Form.Group style={{ width: "100%" }}>
        <Form.Control
          as={"textarea"}
          value={feedback}
          onChange={(event) => setFeedback(event.target.value)}
          placeholder={"Dein Feedback"}
        />
      </Form.Group>
      <NextStepButton
        onClick={confirmOrder ?? goToNextStep}
        isOrderStep={isOrderStep}
        loading={confirmOrderLoading}
        stepActive={stepActive}
      />
    </>
  );
};

export default Step13Feedback;
