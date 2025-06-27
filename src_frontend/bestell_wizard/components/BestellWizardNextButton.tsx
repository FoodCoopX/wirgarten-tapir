import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { NextButtonParameters } from "../types/NextButtonParameters.ts";

interface BestellWizardNextButtonProps {
  params: NextButtonParameters;
  onNextClicked: () => void;
}
const BestellWizardNextButton: React.FC<BestellWizardNextButtonProps> = ({
  params,
  onNextClicked,
}) => {
  return (
    <TapirButton
      icon={params.icon}
      variant={"outline-primary"}
      text={params.text}
      onClick={onNextClicked}
      iconPosition={"right"}
      loading={params.loading}
      disabled={params.disabled}
    />
  );
};

export default BestellWizardNextButton;
