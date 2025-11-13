import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Form } from "react-bootstrap";
import NextStepButton from "../components/NextStepButton.tsx";

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

      <div>
        {settings.distributionChannels.map((channel) => (
          <Form.Group controlId={channel}>
            <Form.Check
              onChange={(event) =>
                updateSelection(channel, event.target.checked)
              }
              required={true}
              checked={selectedDistributionChannels.has(channel)}
              label={channel}
            />
          </Form.Group>
        ))}
      </div>
      <NextStepButton onClick={goToNextStep} />
    </>
  );
};

export default Step12Channel;
