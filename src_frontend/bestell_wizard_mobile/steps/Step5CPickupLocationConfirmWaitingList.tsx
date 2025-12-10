import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
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
            setCurrentStep("5b_pickup_location_choice");
            setCurrentTab("wishes");
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

export default Step5BPickupLocationConfirmWaitingList;
