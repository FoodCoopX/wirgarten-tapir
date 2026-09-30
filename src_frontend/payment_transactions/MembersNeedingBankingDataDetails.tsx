import React from "react";
import { Accordion, Alert, Table } from "react-bootstrap";
import { MemberNeedingBankingData } from "../api-client";

interface MembersNeedingBankingDataDetailsProps {
  members: MemberNeedingBankingData[];
}

const MembersNeedingBankingDataDetails: React.FC<
  MembersNeedingBankingDataDetailsProps
> = ({ members }) => {
  return (
    <>
      <Alert variant={"warning"}>
        <p className={"mb-2"}>
          <strong>Achtung:</strong> Die untenstehenden Benutzer:innen haben
          unvollständige Bankdaten (IBAN, Kontoinhaber:in oder SEPA-Zustimmung
          fehlt).
        </p>
        <p className={"mb-2"}>
          Eine fehlende IBAN führt zu einem leeren IBAN-Feld in CSV- und
          XML-Datei — die XML-Datei wird dadurch für die Bank ungültig, die
          CSV-Datei bleibt vorerst weiterhin nutzbar (z.B. in einem
          Zahlungsverkehrsprogramm). Dort kann dann händisch eine IBAN eingefügt
          werden.
        </p>
        <p className={"mb-2"}>
          Wir empfehlen, bei den angezeigten Benutzer:innen die fehlenden
          Bankdaten anzufragen und zu ergänzen/ergänzen zu lassen.
        </p>
        <p className={"mb-0"}>
          Sofern IBAN und Kontoinhaber:in bereits hinterlegt sind, und die
          Benutzer:innen dennoch hier in der Liste auftauchen, wende dich bitte
          an FoodCoopX um eine fehlende SEPA-Zustimmung zu prüfen.
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
                    <td>{member.firstName}</td>
                    <td>{member.lastName}</td>
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

export default MembersNeedingBankingDataDetails;
