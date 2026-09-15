import React from "react";
import { Accordion, Alert, Table } from "react-bootstrap";
import { MemberWithoutIban } from "../api-client";

interface MembersWithoutIbanDetailsProps {
  members: MemberWithoutIban[];
}

const MembersWithoutIbanDetails: React.FC<MembersWithoutIbanDetailsProps> = ({
  members,
}) => {
  return (
    <>
      <Alert variant={"warning"}>
        <p className={"mb-2"}>
          <strong>Achtung:</strong> Es existieren Benutzer:innen ohne IBAN. Wenn
          du die CSV- und XML-Dateien neu erzeugst, werden diese Mitglieder
          nicht ausgeschlossen. Ihre Zahlungen erscheinen weiterhin in beiden
          Dateien, aber mit leerem IBAN-Feld. Die CSV-Datei ist weiterhin
          nutzbar in einem weiterführenden Schritt (z.B.
          Zahlungsverkehrsprogramm).
        </p>
        <p className={"mb-2"}>
          Die XML-Datei wird dagegen für die Bank nicht mehr lesbar sein.
        </p>
        <p className={"mb-0"}>
          Wir empfehlen die Ergänzung der nicht vorhandenen IBANs vor der
          erneuten Erzeugung der CSV- und XML-Dateien.
        </p>
      </Alert>
      <Accordion>
        <Accordion.Item eventKey={"0"}>
          <Accordion.Header>
            Betroffene Benutzer:innen anzeigen ({members.length})
          </Accordion.Header>
          <Accordion.Body>
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
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
    </>
  );
};

export default MembersWithoutIbanDetails;
