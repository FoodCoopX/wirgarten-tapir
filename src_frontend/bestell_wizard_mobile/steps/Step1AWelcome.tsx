import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

interface Step1AIntroProps {
  goToNextStep: () => void;
  settings: BestellWizardSettings;
}

const Step1AWelcome: React.FC<Step1AIntroProps> = ({
  goToNextStep,
  settings,
}) => {
  return (
    <>
      {settings.strings.step1aText && <p>{settings.strings.step1aText}</p>}
      <TapirButton
        variant={"outline-secondary"}
        text={"Starten"}
        onClick={goToNextStep}
        icon={"keyboard_arrow_down"}
      />
    </>
  );
};

export default Step1AWelcome;
