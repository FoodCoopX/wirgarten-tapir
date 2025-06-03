import React from "react";
import { TapirTheme } from "../types/TapirTheme.ts";
import BestellWizardProductTypeBiotop from "./biotop/BestellWizardProductTypeBiotop.tsx";
import { PublicProductType } from "../api-client";
import { ShoppingCart } from "./ShoppingCart.ts";

interface BestellWizardProductTypeProps {
  theme: TapirTheme;
  productType: PublicProductType;
  onProductTypeNextClicked: () => void;
  onProductTypePreviousClicked: () => void;
  shoppingCart: ShoppingCart;
  setShoppingCart: (shoppingCart: ShoppingCart) => void;
}

const BestellWizardProductType: React.FC<BestellWizardProductTypeProps> = ({
  theme,
  productType,
  onProductTypeNextClicked,
  onProductTypePreviousClicked,
  shoppingCart,
  setShoppingCart,
}) => {
  return (
    <>
      {theme === "biotop" && (
        <BestellWizardProductTypeBiotop
          productType={productType}
          onProductTypeNextClicked={onProductTypeNextClicked}
          onProductTypePreviousClicked={onProductTypePreviousClicked}
          shoppingCart={shoppingCart}
          setShoppingCart={setShoppingCart}
        />
      )}
    </>
  );
};

export default BestellWizardProductType;
