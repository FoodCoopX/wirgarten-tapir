import React from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../../components/TapirButton.tsx";

interface GeneralWaitingListModalProps {
  show: boolean;
  confirmEnableWaitingListMode: () => void;
}

const GeneralWaitingListModal: React.FC<GeneralWaitingListModalProps> = ({
  show,
  confirmEnableWaitingListMode,
}) => {
  return (
    <Modal
      show={show}
      centered={true}
      onHide={confirmEnableWaitingListMode}
      size={"lg"}
    >
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Warteliste</h5>
      </Modal.Header>
      <Modal.Body>
        <p>
          Derzeit sind keine Ernteanteile verfügbar. Du kannst dich aber auf die
          Warteliste setzen lassen. Wir kontaktieren dich, sobald ein Platz
          freigeworden ist.
        </p>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"Weiter mit Warteliste-Eintrag"}
          variant={"primary"}
          onClick={confirmEnableWaitingListMode}
          icon={"pending_actions"}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default GeneralWaitingListModal;
