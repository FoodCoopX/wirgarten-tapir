import React from "react";
import { Card, Col, Row, Table } from "react-bootstrap";

interface WaitingListCardProps {
  csrfToken: string;
}

const WaitingListCard: React.FC<WaitingListCardProps> = ({ csrfToken }) => {
  return (
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={
                  "d-flex justify-content-between align-items-center mb-0"
                }
              >
                <h5 className={"mb-0"}>Warteliste</h5>
              </div>
            </Card.Header>
            <Card.Body className={"p-0"}>
              <Table striped hover responsive>
                <thead>
                  <tr>
                    <th>Mitgliedsnummer</th>
                    <th>Eintragungsdatum auf Warteliste</th>
                    <th>Vorname</th>
                    <th>Nachname</th>
                    <th>Email-Adresse</th>
                    <th>Telefonnummer</th>
                    <th>Wohnort</th>
                    <th>Geno-Beitrittsdatum</th>
                    <th>Aktuelle Produkte</th>
                    <th>Gewünschte Produkte</th>
                    <th>Derzeitiger Verteilort</th>
                    <th>Verteilort Prioritäten</th>
                    <th>Wunsch-Startdatum</th>
                  </tr>
                </thead>
              </Table>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default WaitingListCard;
