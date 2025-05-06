import React from "react";
import { Card, Col, Row } from "react-bootstrap";

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
                <h5 className={"mb-0"}>YOYOYO</h5>
              </div>
            </Card.Header>
            <Card.Body>Coucou</Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default WaitingListCard;
