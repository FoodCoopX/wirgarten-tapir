import React from "react";

interface BestellWizardProps {
  csrfToken: string;
}

const BestellWizard: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  return <>Prout {csrfToken}</>;
};

export default BestellWizard;
