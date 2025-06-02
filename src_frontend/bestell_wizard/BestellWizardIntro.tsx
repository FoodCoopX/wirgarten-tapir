import React from "react";
import { TapirTheme } from "../types/tapirTheme.ts";
import BestellWizardIntroL2g from "./l2g/BestellWizardIntroL2g.tsx";
import BestellWizardIntroBiotop from "./biotop/BestellWizardIntroBiotop.tsx";

interface BestellWizardIntroProps {
  theme: TapirTheme;
}

const BestellWizardIntro: React.FC<BestellWizardIntroProps> = ({ theme }) => {
  const intros: { [K in TapirTheme]: React.FC } = {
    l2g: BestellWizardIntroL2g,
    biotop: BestellWizardIntroBiotop,
  };
  return (
    <>
      {theme === "biotop" && <BestellWizardIntroBiotop />}
      {theme === "l2g" && <BestellWizardIntroL2g />}
    </>
  );
};

export default BestellWizardIntro;
