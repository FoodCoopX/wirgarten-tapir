import React from "react";
import { PublicProduct, PublicProductType } from "../../api-client";
import { Modal } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { shouldShowWarningProductNotAvailable } from "../../utils/shouldShowWarningNotAvailable.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

interface Step4BProductDetailModalProps {
  productType: PublicProductType;
  product: PublicProduct;
  show: boolean;
  onHide: () => void;
  settings: BestellWizardSettings;
}

const Step4BProductDetailModal: React.FC<Step4BProductDetailModalProps> = ({
  productType,
  product,
  show,
  onHide,
  settings,
}) => {
  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton={true}>
        {productType.name} {product.name}
      </Modal.Header>
      <Modal.Body>
        <span>
          Basisbeitrag: {formatCurrency(product.price)} pro Monat inkl.
          MwSt.{" "}
        </span>
        <br />
        {shouldShowWarningProductNotAvailable(
          product,
          productType,
          settings,
        ) && (
          <>
            <span className={"text-danger"}>
              (nur Warteliste-Eintrag möglich)
            </span>
            <br />
          </>
        )}
        <span>{product.descriptionInBestellwizard}</span>
      </Modal.Body>
    </Modal>
  );
};

export default Step4BProductDetailModal;
