import React from "react";
import { TapirTheme } from "../types/TapirTheme.ts";
import BestellWizardIntroL2g from "./l2g/BestellWizardIntroL2g.tsx";
import BestellWizardIntroBiotop from "./biotop/BestellWizardIntroBiotop.tsx";
import { PublicProductType } from "../api-client";

interface BestellWizardIntroProps {
  theme: TapirTheme;
  selectedProductTypes: PublicProductType[];
  setSelectedProductTypes: (selectedProductTypes: PublicProductType[]) => void;
  onIntroNextClicked: () => void;
  publicProductTypes: PublicProductType[];
}

const BestellWizardIntro: React.FC<BestellWizardIntroProps> = ({
  theme,
  selectedProductTypes,
  setSelectedProductTypes,
  onIntroNextClicked,
  publicProductTypes,
}) => {
  return (
    <>
      {theme === "biotop" && (
        <BestellWizardIntroBiotop
          selectedProductTypes={selectedProductTypes}
          setSelectedProductTypes={setSelectedProductTypes}
          onIntroNextClicked={onIntroNextClicked}
          publicProductTypes={publicProductTypes}
        />
      )}
      {theme === "l2g" && <BestellWizardIntroL2g />}
    </>
  );
};

export default BestellWizardIntro;
