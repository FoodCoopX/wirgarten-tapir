import React from "react";
import { TapirTheme } from "../types/TapirTheme.ts";
import BestellWizardProductTypeBiotop from "./biotop/BestellWizardProductTypeBiotop.tsx";
import { PublicProductType } from "../api-client";

interface BestellWizardProductTypeProps {
  theme: TapirTheme;
  productType: PublicProductType;
  onProductTypeNextClicked: () => void;
  onProductTypePreviousClicked: () => void;
}

const BestellWizardProductType: React.FC<BestellWizardProductTypeProps> = ({
  theme,
  productType,
  onProductTypeNextClicked,
  onProductTypePreviousClicked,
}) => {
  return (
    <>
      {theme === "biotop" && (
        <BestellWizardProductTypeBiotop
          productType={productType}
          onProductTypeNextClicked={onProductTypeNextClicked}
          onProductTypePreviousClicked={onProductTypePreviousClicked}
        />
      )}
    </>
  );
};

export default BestellWizardProductType;
