import React from "react";

interface BestellWizardCardTitleProps {
  text: string;
}

const BestellWizardCardTitle: React.FC<BestellWizardCardTitleProps> = ({
  text,
}) => {
  return <h3 className={"card-title"}>{text}</h3>;
};

export default BestellWizardCardTitle;
