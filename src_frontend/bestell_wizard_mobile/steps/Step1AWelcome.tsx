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
    <div
      style={{ height: "100%" }}
      className={
        "d-flex align-items-center justify-content-center gap-2 flex-column text-center"
      }
    >
      {settings.strings.step1aTitle && <h1>{settings.strings.step1aTitle}</h1>}
      {settings.strings.step1aText && <p>{settings.strings.step1aText}</p>}
      <TapirButton
        variant={"outline-secondary"}
        text={"Starten"}
        onClick={goToNextStep}
      />
    </div>
  );
};

export default Step1AWelcome;
