import React from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";

type WaitingListMode = "general" | "product";

interface WaitingListModalProps {
  show: boolean;
  onHide: () => void;
  mode: WaitingListMode;
}

const WaitingListModal: React.FC<WaitingListModalProps> = ({
  show,
  onHide,
  mode,
}) => {
  function getBody() {
    switch (mode) {
      case "general":
        return (
          <p>
            Derzeit sind keine Ernteanteile verfügbar. Du kannst dich aber auf
            die Warteliste setzen lassen. Wir kontaktieren dich, sobald ein
            Platz freigeworden ist.
          </p>
        );
      case "product":
        return (
          <>
            <p>
              Derzeit ist deine gewünschte Ernteanteilsgröße nicht verfügbar.
            </p>
            <p>
              Du kannst eine andere Größe wählen, oder dich auf die Warteliste
              setzen lassen. Dafür brauchen wir noch ein paar Angaben von dir.
            </p>
          </>
        );
    }
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Warteliste</h5>
      </Modal.Header>
      <Modal.Body>{getBody()}</Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"OK"}
          variant={"primary"}
          onClick={onHide}
          icon={"check"}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default WaitingListModal;
