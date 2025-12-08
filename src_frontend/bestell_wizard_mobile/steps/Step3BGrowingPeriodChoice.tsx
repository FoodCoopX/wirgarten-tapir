import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { Form } from "react-bootstrap";
import { PublicGrowingPeriod } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

interface Step3BGrowingPeriodChoiceProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  selectedGrowingPeriod: PublicGrowingPeriod | undefined;
  setSelectedGrowingPeriod: (p: PublicGrowingPeriod) => void;
}

const Step3BGrowingPeriodChoice: React.FC<Step3BGrowingPeriodChoiceProps> = ({
  settings,
  goToNextStep,
  selectedGrowingPeriod,
  setSelectedGrowingPeriod,
}) => {
  return (
    <>
      {settings.strings.step3bText && (
        <p
          className={"text-center"}
          dangerouslySetInnerHTML={{ __html: settings.strings.step3bText }}
        />
      )}
      <div className={"d-flex flex-row gap-2"}>
        {settings.growingPeriodChoices.map((growingPeriod) => (
          <div key={growingPeriod.id}>
            <input
              type="checkbox"
              className="btn-check"
              id={growingPeriod.id}
              autoComplete="off"
              onChange={() => setSelectedGrowingPeriod(growingPeriod)}
              checked={growingPeriod === selectedGrowingPeriod}
              disabled={settings.growingPeriodChoices.length === 1}
            />
            <label
              className={"btn btn-" + BUTTON_VARIANT}
              htmlFor={growingPeriod.id}
            >
              <div className={"d-flex flex-row gap-2 align-items-center"}>
                <Form.Check
                  checked={growingPeriod === selectedGrowingPeriod}
                  readOnly={true}
                  style={{ pointerEvents: "none" }}
                  type={"radio"}
                />
                <span>
                  {formatDateNumeric(growingPeriod.contractStartDate)}
                </span>
              </div>
            </label>
          </div>
        ))}
      </div>
      <NextStepButton onClick={goToNextStep} />
    </>
  );
};

export default Step3BGrowingPeriodChoice;
