import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import TapirCheckbox from "../components/TapirCheckbox.tsx";

interface Step12ChannelProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  selectedDistributionChannels: Set<string>;
  setSelectedDistributionChannels: (set: Set<string>) => void;
}

const Step12Channel: React.FC<Step12ChannelProps> = ({
  settings,
  goToNextStep,
  selectedDistributionChannels,
  setSelectedDistributionChannels,
}) => {
  function updateSelection(channel: string, selected: boolean) {
    if (selected) {
      selectedDistributionChannels.add(channel);
    } else {
      selectedDistributionChannels.delete(channel);
    }
    setSelectedDistributionChannels(new Set(selectedDistributionChannels));
  }

  return (
    <>
      <p className={"text-center"}>
        Mehrfachauswahl möglich
        <br />
        Ist gerade nur als Platzhalder da, der Auswahl wird nicht gespeichert
      </p>

      <div className={"d-flex flex-column gap-2"}>
        {settings.distributionChannels.map((channel) => (
          <TapirCheckbox
            checked={selectedDistributionChannels.has(channel)}
            onChange={(checked) => updateSelection(channel, checked)}
            controlId={"distribution_channels_" + channel}
            label={channel}
          />
        ))}
      </div>
      <NextStepButton onClick={goToNextStep} />
    </>
  );
};

export default Step12Channel;
