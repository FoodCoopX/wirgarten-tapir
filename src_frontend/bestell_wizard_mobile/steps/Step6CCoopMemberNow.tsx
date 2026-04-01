import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import "../utils/flexColOnSmallScreen.css";
import { Step } from "../types/Step.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

interface Step6CCoopMemberNowProps {
  settings: BestellWizardSettings;
  setCurrentStep: (step: Step) => void;
  setBecomeMemberNow: (becomeMemberNow: boolean) => void;
}

const Step6CCoopMemberNow: React.FC<Step6CCoopMemberNowProps> = ({
  settings,
  setCurrentStep,
  setBecomeMemberNow,
}) => {
  return (
    <>
      <p
        dangerouslySetInnerHTML={{ __html: settings.strings.step6cText }}
        className={"text-center"}
      />
      <div className={"d-flex flex-row gap-2"}>
        <TapirButton
          text={"Nein"}
          variant={BUTTON_VARIANT}
          onClick={() => {
            setBecomeMemberNow(false);
            setTimeout(() => setCurrentStep("8_personal_data"), 1);
          }}
          icon={"pending_actions"}
        />
        <TapirButton
          text={"Ja"}
          variant={BUTTON_VARIANT}
          onClick={() => {
            setBecomeMemberNow(true);
            setTimeout(() => setCurrentStep("6b_coop_shares"), 50);
          }}
          icon={"id_card"}
        />
      </div>
    </>
  );
};

export default Step6CCoopMemberNow;
