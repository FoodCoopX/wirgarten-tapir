import React from "react";
import { Modal } from "react-bootstrap";
import { MemberWithoutIban } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import MembersWithoutIbanDetails from "./MembersWithoutIbanDetails.tsx";

interface MembersWithoutIbanRebuildWarningModalProps {
  show: boolean;
  members: MemberWithoutIban[];
  onCancel: () => void;
  onContinue: () => void;
}

const MembersWithoutIbanRebuildWarningModal: React.FC<
  MembersWithoutIbanRebuildWarningModalProps
> = ({ show, members, onCancel, onContinue }) => {
  return (
    <Modal show={show} onHide={onCancel} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>Mitglieder ohne IBAN in diesem Monat</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <MembersWithoutIbanDetails members={members} />
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"Abbrechen"}
          variant={"outline-secondary"}
          onClick={onCancel}
        />
        <TapirButton
          text={"Trotzdem fortfahren"}
          variant={"danger"}
          icon={"warning"}
          onClick={onContinue}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default MembersWithoutIbanRebuildWarningModal;
