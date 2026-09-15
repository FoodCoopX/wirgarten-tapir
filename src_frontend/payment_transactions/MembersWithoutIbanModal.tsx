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
          <p className={"mb-2"}>
            <strong>Achtung:</strong> Diese Mitglieder werden beim Erzeugen der
            CSV- und XML-Dateien nicht ausgeschlossen. Ihre Zahlungen erscheinen
            weiterhin in beiden Dateien, aber mit leerem IBAN-Feld. Die
            CSV-Datei ist somit weiterhin nutzbar in einem weiterführenden
            Schritt (z.B. Zahlungsverkehrsprogramm).
          </p>
          <p className={"mb-2"}>
            Die XML-Datei wird dagegen für die Bank nicht mehr lesbar sein.
          </p>
          <p className={"mb-0"}>
            Bitte ergänzt die IBAN, bevor ihr die Dateien neu erzeugt und dann
            im Online-Banking hochladet.
          </p>
        </Alert>
        <Table responsive hover striped bordered>
          <thead>
            <tr>
              <th>Mitgliedsnummer</th>
              <th>Vorname</th>
              <th>Nachname</th>
              <th>E-Mail</th>
              <th>Telefonnummer</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member, index) => (
              <tr key={index}>
                <td>
                  <a href={member.memberUrl}>{member.memberNo}</a>
                </td>
                <td>
                  <a href={member.memberUrl}>{member.firstName}</a>
                </td>
                <td>
                  <a href={member.memberUrl}>{member.lastName}</a>
                </td>
                <td>
                  {member.email && (
                    <a href={`mailto:${member.email}`}>{member.email}</a>
                  )}
                </td>
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
