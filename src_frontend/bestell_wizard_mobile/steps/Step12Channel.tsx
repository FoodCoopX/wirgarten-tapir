import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import TapirCheckbox from "../components/TapirCheckbox.tsx";

interface Step12ChannelProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  selectedDistributionChannels: Set<string>;
  setSelectedDistributionChannels: (set: Set<string>) => void;
  confirmOrder: (() => void) | undefined;
  confirmOrderLoading: boolean;
}

const Step12Channel: React.FC<Step12ChannelProps> = ({
  settings,
  goToNextStep,
  selectedDistributionChannels,
  setSelectedDistributionChannels,
  confirmOrder,
  confirmOrderLoading,
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
      <p className={"text-center"}>Mehrfachauswahl möglich</p>

      <div className={"d-flex flex-column gap-2"}>
        {Object.entries(settings.distributionChannels).map(
          ([channelId, channelName]) => (
            <TapirCheckbox
              key={channelId}
              checked={selectedDistributionChannels.has(channelId)}
              onChange={(checked) => updateSelection(channelId, checked)}
              controlId={"distribution_channels_" + channelId}
              label={channelName}
            />
          ),
        )}
      </div>
      <NextStepButton
        onClick={confirmOrder ?? goToNextStep}
        isOrderStep={!settings.feedbackStepEnabled}
        loading={confirmOrderLoading}
      />
    </>
  );
};

export default Step12Channel;
