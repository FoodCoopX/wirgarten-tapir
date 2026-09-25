import React from "react";
import { Modal } from "react-bootstrap";
import { MemberNeedingBankingData } from "../api-client";
import MembersNeedingBankingDataDetails from "./MembersNeedingBankingDataDetails.tsx";

interface MembersNeedingBankingDataModalProps {
  show: boolean;
  onHide: () => void;
  members: MemberNeedingBankingData[];
}

const MembersNeedingBankingDataModal: React.FC<
  MembersNeedingBankingDataModalProps
> = ({ show, onHide, members }) => {
  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>Benutzer:innen mit unvollständigen Bankdaten</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <MembersNeedingBankingDataDetails members={members} />
      </Modal.Body>
    </Modal>
  );
};

export default MembersNeedingBankingDataModal;
