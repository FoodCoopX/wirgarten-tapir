import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";

interface Step14ConfirmationProps {
  settings: BestellWizardSettings;
  memberMail: string;
}

const Step14Confirmation: React.FC<Step14ConfirmationProps> = ({
  settings,
  memberMail,
}) => {
  return (
    <>
      <p
        className={"text-center"}
        dangerouslySetInnerHTML={getHtmlDescription(
          settings.strings.step14Text.replace(
            "{{mitglieder_mail}}",
            memberMail,
          ),
        )}
      />
    </>
  );
};

export default Step14Confirmation;
