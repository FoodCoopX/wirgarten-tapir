import React from "react";
import { Modal } from "react-bootstrap";
import { MemberWithoutIban } from "../api-client";
import MembersWithoutIbanDetails from "./MembersWithoutIbanDetails.tsx";

interface MembersWithoutIbanModalProps {
  show: boolean;
  onHide: () => void;
  members: MemberWithoutIban[];
}

const MembersWithoutIbanModal: React.FC<MembersWithoutIbanModalProps> = ({
  show,
  onHide,
  members,
}) => {
  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>Benutzer:innen ohne IBAN</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <MembersWithoutIbanDetails members={members} />
      </Modal.Body>
    </Modal>
  );
};

export default MembersWithoutIbanModal;
