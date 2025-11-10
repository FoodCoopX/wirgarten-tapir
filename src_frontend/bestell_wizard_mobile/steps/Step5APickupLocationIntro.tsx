import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";

interface Step5APickupLocationIntroProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
}

const Step5APickupLocationIntro: React.FC<Step5APickupLocationIntroProps> = ({
  settings,
  goToNextStep,
}) => {
  return (
    <>
      <div
        style={{ height: "80dvh", display: "flex", flexDirection: "column" }}
        className={"d-flex flex-column gap-2 mx-2 px-4"}
      >
        <div
          style={{
            maxHeight: "70dvh",
            overflowY: "scroll",
          }}
        >
          <div
            className={
              "d-flex align-items-center justify-content-center gap-2 flex-column"
            }
            style={{ minHeight: "70dvh" }}
          >
            <h1 className={"text-center"}>{settings.strings.step5aTitle}</h1>
            <div
              dangerouslySetInnerHTML={getHtmlDescription(
                settings.strings.step5aText,
              )}
            />
          </div>
        </div>
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
            icon={"keyboard_arrow_down"}
          />
        </div>
      </div>
    </>
  );
};

export default Step5APickupLocationIntro;
