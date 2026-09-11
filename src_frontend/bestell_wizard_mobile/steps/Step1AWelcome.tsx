import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";

interface Step1AIntroProps {
  goToNextStep: () => void;
  settings: BestellWizardSettings;
  stepActive: boolean;
}

const Step1AWelcome: React.FC<Step1AIntroProps> = ({
  goToNextStep,
  settings,
  stepActive,
}) => {
  return (
    <>
      {settings.strings.step1aText && (
        <p
          className={"text-center"}
          dangerouslySetInnerHTML={{ __html: settings.strings.step1aText }}
        />
      )}
      <NextStepButton
        text={"Starten"}
        onClick={goToNextStep}
        stepActive={stepActive}
      />
    </>
  );
};

export default Step1AWelcome;
