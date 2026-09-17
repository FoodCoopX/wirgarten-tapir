import React from "react";
import { Modal } from "react-bootstrap";
import { MemberNeedingBankingData } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import MembersNeedingBankingDataDetails from "./MembersNeedingBankingDataDetails.tsx";

interface MembersNeedingBankingDataRebuildWarningModalProps {
  show: boolean;
  members: MemberNeedingBankingData[];
  onCancel: () => void;
  onContinue: () => void;
}

const MembersNeedingBankingDataRebuildWarningModal: React.FC<
  MembersNeedingBankingDataRebuildWarningModalProps
> = ({ show, members, onCancel, onContinue }) => {
  return (
    <Modal show={show} onHide={onCancel} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>Mitglieder mit unvollständigen Bankdaten</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <MembersNeedingBankingDataDetails members={members} />
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"Abbrechen"}
          variant={"outline-secondary"}
          onClick={onCancel}
        />
        <TapirButton
          text={"Trotzdem fortfahren"}
          variant={"outline-primary"}
          icon={"warning"}
          onClick={onContinue}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default MembersNeedingBankingDataRebuildWarningModal;
