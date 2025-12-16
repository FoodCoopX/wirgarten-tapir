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

function getPeriodName(period: PublicGrowingPeriod) {
  if (period.startDate > new Date()) {
    return "Ab dem " + formatDateNumeric(period.startDate);
  }
  return "Ab sofort";
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
      <div className={"d-flex flex-row gap-3"}>
        {settings.growingPeriodChoices.map((growingPeriod) => (
          <div key={growingPeriod.id} className={"d-flex flex-column gap-2"}>
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
                <span>{getPeriodName(growingPeriod)}</span>
              </div>
            </label>
            <small className={"text-center"}>
              Vertragsstart {formatDateNumeric(growingPeriod.contractStartDate)}
            </small>
          </div>
        ))}
      </div>
      <NextStepButton onClick={goToNextStep} />
    </>
  );
};

export default Step3BGrowingPeriodChoice;
