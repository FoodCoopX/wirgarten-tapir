import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { Step } from "../types/Step.ts";
import { PickupLocationTab } from "../types/PickupLocationTab.ts";

interface Step5BPickupLocationConfirmWaitingListProps {
  settings: BestellWizardSettings;
  setCurrentStep: (step: Step) => void;
  goToNextStep: () => void;
  setCurrentTab: (tab: PickupLocationTab) => void;
}

const Step5BPickupLocationConfirmWaitingList: React.FC<
  Step5BPickupLocationConfirmWaitingListProps
> = ({ settings, setCurrentStep, goToNextStep, setCurrentTab }) => {
  return (
    <>
      <p dangerouslySetInnerHTML={{ __html: settings.strings.step5cText }} />
      <TapirButton
        variant={BUTTON_VARIANT}
        text={"Weitere Wünsche eintragen"}
        icon={"keyboard_arrow_up"}
        onClick={() => {
          setCurrentStep("5b_pickup_location_choice");
          setCurrentTab("wishes");
        }}
      />
      <NextStepButton
        onClick={goToNextStep}
        text={"Mit nur einen Wunsch weitergehen"}
      />
    </>
  );
};

export default Step5BPickupLocationConfirmWaitingList;
