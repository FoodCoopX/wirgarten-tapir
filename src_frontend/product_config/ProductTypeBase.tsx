import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import {
  getPeriodIdFromUrl,
  getProductTypeIdFromUrl,
} from "./get_parameter_from_url.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import ProductTypeEditModal from "./ProductTypeEditModal.tsx";
import ProductTypeCreateModal from "./ProductTypeCreateModal.tsx";

interface ProductTypeBaseProps {
  csrfToken: string;
}

const ProductTypeBase: React.FC<ProductTypeBaseProps> = ({ csrfToken }) => {
  const [showEditModal, setShowEditModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function onEditClick() {
    if (!getProductTypeIdFromUrl()) {
      alert(
        "Du musst erst das Produkt-Typ das du editieren möchtest auswählen.",
      );
      return;
    }
    setShowEditModal(true);
  }

  function onCreateClick() {
    if (!getPeriodIdFromUrl()) {
      alert("Du musst erst eine Vertragsperiode auswählen.");
      return;
    }
    setShowCreateModal(true);
  }

  return (
    <>
      <span className={"d-flex flex-row gap-2"}>
        <TapirButton
          icon={"add"}
          variant={"outline-primary"}
          onClick={onCreateClick}
        />
        <TapirButton
          icon={"edit"}
          variant={"outline-primary"}
          onClick={onEditClick}
        />
      </span>
      <ProductTypeCreateModal
        csrfToken={csrfToken}
        show={showCreateModal}
        onHide={() => setShowCreateModal(false)}
        setToastDatas={setToastDatas}
      />
      <ProductTypeEditModal
        csrfToken={csrfToken}
        show={showEditModal}
        onHide={() => setShowEditModal(false)}
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
