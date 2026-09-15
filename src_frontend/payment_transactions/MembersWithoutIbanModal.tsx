import React from "react";
import { Alert, Modal, Table } from "react-bootstrap";
import { MemberWithoutIban } from "../api-client";

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
        <Alert variant={"warning"}>
          Diese Mitglieder werden beim Erzeugen der CSV- und XML-Dateien{" "}
          <strong>nicht ausgeschlossen</strong>. Ihre Zahlungen erscheinen
          weiterhin in beiden Dateien, aber mit leerem IBAN-Feld. In der
          XML-Datei entsteht dadurch ein leeres IBAN-Element, was die Datei für
          die Bank ungültig macht. Bitte die IBAN ergänzen, bevor die
          Lastschriften eingereicht werden.
        </Alert>
        <Table responsive hover striped bordered>
          <thead>
            <tr>
              <th>Vorname</th>
              <th>Nachname</th>
              <th>E-Mail</th>
              <th>Telefonnummer</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member, index) => (
              <tr key={index}>
                <td>{member.firstName}</td>
                <td>{member.lastName}</td>
                <td>{member.email}</td>
                <td>{member.phoneNumber}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Modal.Body>
    </Modal>
  );
};

export default MembersWithoutIbanModal;
