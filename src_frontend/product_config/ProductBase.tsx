import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import { getProductIdFromUrl } from "./get_parameter_from_url.ts";
import ProductModal from "./ProductModal.tsx";

interface ProductBaseProps {
  csrfToken: string;
}

const ProductBase: React.FC<ProductBaseProps> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);

  function onClick() {
    if (!getProductIdFromUrl()) {
      alert("Du musst erst das Produkt das du editieren möchtest auswählen.");
      return;
    }
    setShowModal(true);
  }
  return (
    <>
      <TapirButton
        icon={"edit"}
        variant={"outline-primary"}
        onClick={onClick}
      />
      <ProductModal
        csrfToken={csrfToken}
        show={showModal}
        onHide={() => setShowModal(false)}
      />
    </>
  );
};

export default ProductBase;
