import React from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProductType } from "../../api-client";

interface ProductWaitingListModalProps {
  show: boolean;
  onHide: () => void;
  confirmEnableWaitingListMode: () => void;
  productType: PublicProductType | undefined;
}

const ProductWaitingListModal: React.FC<ProductWaitingListModalProps> = ({
  show,
  onHide,
  confirmEnableWaitingListMode,
  productType,
}) => {
  return (
    <Modal show={show} centered={true} onHide={onHide} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Warteliste</h5>
      </Modal.Header>
      <Modal.Body>
        <p>
          Derzeit ist deine gewünschte {productType?.name}-Größe nicht
          verfügbar.
        </p>
        <p>
          {productType?.forceWaitingList
            ? "Du kannst dich auf die Warteliste setzen lassen."
            : "Du kannst eine andere Größe wählen, oder dich auf die Warteliste setzen lassen."}
          Dafür brauchen wir noch ein paar Angaben von dir.
        </p>
      </Modal.Body>
      <Modal.Footer>
        <div
          className={"d-flex flex-row justify-content-between gap-2"}
          style={{ width: "100%" }}
        >
          <TapirButton
            text={"Andere Größe wählen"}
            variant={"outline-secondary"}
            onClick={onHide}
            icon={"undo"}
          />
          <TapirButton
            text={"Weiter mit Warteliste-Eintrag"}
            variant={"primary"}
            onClick={confirmEnableWaitingListMode}
            icon={"pending_actions"}
          />
        </div>
      </Modal.Footer>
    </Modal>
  );
};

export default ProductWaitingListModal;
