import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { PickupLocationTab } from "../types/PickupLocationTab.ts";
import { Step } from "../types/Step.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";

interface Step5EPickupLocationConfirmWaitingListProps {
  settings: BestellWizardSettings;
  setCurrentStep: (step: Step) => void;
  goToNextStep: () => void;
  setCurrentTab: (tab: PickupLocationTab) => void;
  pickupLocationChoiceStep: Step;
}

const Step5EPickupLocationConfirmWaitingList: React.FC<
  Step5EPickupLocationConfirmWaitingListProps
> = ({
  settings,
  setCurrentStep,
  goToNextStep,
  setCurrentTab,
  pickupLocationChoiceStep,
}) => {
  return (
    <>
      <p
        className={"text-center"}
        dangerouslySetInnerHTML={{ __html: settings.strings.step5cText }}
      />
      <div className={"d-flex flex-row gap-2"}>
        <TapirButton
          variant={BUTTON_VARIANT}
          text={"Ja"}
          icon={"keyboard_arrow_up"}
          onClick={() => {
            setCurrentStep(pickupLocationChoiceStep);
            setCurrentTab("map");
          }}
        />
        <TapirButton
          onClick={goToNextStep}
          text={"Nein"}
          variant={BUTTON_VARIANT}
          icon={"keyboard_arrow_down"}
        />
      </div>
    </>
  );
};

export default Step5EPickupLocationConfirmWaitingList;
