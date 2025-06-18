import React from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../../components/TapirButton.tsx";

interface PickupLocationWaitingListModalProps {
  show: boolean;
  onHide: () => void;
  confirmEnableWaitingListMode: () => void;
}

const PickupLocationWaitingListModal: React.FC<
  PickupLocationWaitingListModalProps
> = ({ show, onHide, confirmEnableWaitingListMode }) => {
  return (
    <Modal show={show} centered={true} onHide={onHide} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Warteliste</h5>
      </Modal.Header>
      <Modal.Body>
        <p>Die ausgewählte Verteilstation ist derzeit ausgelastet.</p>
        <p>
          Du kannst eine andere Station wählen, oder dich auf die Warteliste
          setzen lassen. In dem Fall kannst du mehrere Wünsche eintragen, um
          vielleicht früher einsteigen zu dürfen.
        </p>
      </Modal.Body>
      <Modal.Footer>
        <div
          className={"d-flex flex-row justify-content-between gap-2"}
          style={{ width: "100%" }}
        >
          <TapirButton
            text={"Andere Station wählen"}
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

export default PickupLocationWaitingListModal;
