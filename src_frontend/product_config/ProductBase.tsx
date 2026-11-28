import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import { getProductIdFromUrl } from "./get_parameter_from_url.ts";
import ProductModal from "./ProductModal.tsx";

const ProductBase: React.FC = () => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function onClick() {
    if (!getProductIdFromUrl()) {
      alert(
        "Du musst erst die Anteilsgröße, die du editieren möchtest, auswählen.",
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
      <ProductModal
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

export default ProductBase;
