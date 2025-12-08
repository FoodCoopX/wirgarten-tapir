import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";

interface Step14BConfirmationWaitingListProps {
  settings: BestellWizardSettings;
  memberMail: string;
}

const Step14BConfirmationWaitingList: React.FC<
  Step14BConfirmationWaitingListProps
> = ({ settings, memberMail }) => {
  return (
    <>
      <p
        className={"text-center"}
        dangerouslySetInnerHTML={getHtmlDescription(
          settings.strings.step14bText
            .replace("{{mitglieder_mail}}", memberMail)
            .replace("{{kontakt_mail}}", settings.contactMailAddress),
        )}
      />
    </>
  );
};

export default Step14BConfirmationWaitingList;
