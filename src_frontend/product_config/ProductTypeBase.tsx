import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import { getProductTypeIdFromUrl } from "./get_parameter_from_url.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import ProductTypeModal from "./ProductTypeModal.tsx";

interface ProductTypeBaseProps {
  csrfToken: string;
}

const ProductTypeBase: React.FC<ProductTypeBaseProps> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function onClick() {
    if (!getProductTypeIdFromUrl()) {
      alert(
        "Du musst erst das Produkt-Typ das du editieren möchtest auswählen.",
      );
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
      <ProductTypeModal
        csrfToken={csrfToken}
        show={showModal}
        onHide={() => setShowModal(false)}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default ProductTypeBase;
