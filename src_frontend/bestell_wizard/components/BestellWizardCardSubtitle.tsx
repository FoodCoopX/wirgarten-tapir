import React from "react";

interface BestellWizardCardSubtitleProps {
  text: string;
}

const BestellWizardCardSubtitle: React.FC<BestellWizardCardSubtitleProps> = ({
  text,
}) => {
  return <h4 className={"card-subtitle"}>{text}</h4>;
};

export default BestellWizardCardSubtitle;
