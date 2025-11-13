import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";

interface Step14ConfirmationProps {
  settings: BestellWizardSettings;
}

const Step14Confirmation: React.FC<Step14ConfirmationProps> = ({
  settings,
}) => {
  return (
    <>
      <p
        className={"text-center"}
        dangerouslySetInnerHTML={getHtmlDescription(
          settings.strings.step14Text,
        )}
      />
    </>
  );
};

export default Step14Confirmation;
