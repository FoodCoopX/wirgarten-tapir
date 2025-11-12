import React, { useEffect, useRef } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { replaceTokens } from "../utils/replaceTokens.ts";
import StepTitle from "../components/StepTitle.tsx";
import { Form } from "react-bootstrap";

interface Step12ChannelProps {
  settings: BestellWizardSettings;
  active: boolean;
  goToNextStep: () => void;
  firstName: string;
  selectedDistributionChannels: Set<string>;
  setSelectedDistributionChannels: (set: Set<string>) => void;
}

const Step12Channel: React.FC<Step12ChannelProps> = ({
  settings,
  active,
  goToNextStep,
  firstName,
  selectedDistributionChannels,
  setSelectedDistributionChannels,
}) => {
  const scrollDiv = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !scrollDiv.current) {
      return;
    }

    scrollDiv.current.scrollTop = 0;
  }, [active]);

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
      <div
        style={{ height: "80dvh", display: "flex", flexDirection: "column" }}
        className={"d-flex flex-column gap-2 mx-2"}
      >
        <div
          style={{
            maxHeight: "70dvh",
            overflowY: "scroll",
          }}
          ref={scrollDiv}
        >
          <div
            className={
              "d-flex align-items-center justify-content-center gap-2 flex-column mx-4"
            }
            style={{ minHeight: "70dvh" }}
          >
            <StepTitle
              title={replaceTokens(settings.strings.step12Title, firstName)}
            />
            <p className={"text-center"}>Mehrfachauswahl möglich</p>
            <p className={"text-center"}>
              Ist gerade nur als Platzhalder da, der Auswahl wird nicht
              gespeichert
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

export default Step12Channel;
