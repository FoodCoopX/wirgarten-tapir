import React from "react";
import { Button, Card, Col, Form, Row } from "react-bootstrap";

import { BiddingRoundsApi } from "../../api-client/apis/BiddingRoundsApi.ts";
import { Round } from "../../api-client/models/Round.ts";

interface LockAverageBidCardProps {
  round: Round;
  isLocked: boolean;
  busy: boolean;
  api: BiddingRoundsApi;
  roundId: string;
  runAction: (action: () => Promise<unknown>, message: string) => Promise<void>;
  lockPosition: number;
  setLockPosition: React.Dispatch<React.SetStateAction<number>>;
  surchargePercent: string;
  setSurchargePercent: React.Dispatch<React.SetStateAction<string>>;
  surchargeOnBids: boolean;
  setSurchargeOnBids: React.Dispatch<React.SetStateAction<boolean>>;
  surchargeOnAverage: boolean;
  setSurchargeOnAverage: React.Dispatch<React.SetStateAction<boolean>>;
}

const LockAverageBidCard: React.FC<LockAverageBidCardProps> = ({
  round,
  isLocked,
  busy,
  api,
  roundId,
  runAction,
  lockPosition,
  setLockPosition,
  surchargePercent,
  setSurchargePercent,
  surchargeOnBids,
  setSurchargeOnBids,
  surchargeOnAverage,
  setSurchargeOnAverage,
}) => {
  return (
    <Card className={"mb-4"}>
      <Card.Header>
        <strong>Durchschnittsgebot fixieren</strong>
      </Card.Header>
      <Card.Body>
        {isLocked ? (
          <>
            <p className={"mb-2"}>
              Fixiert bei Position{" "}
              <strong>{Number(round.lockedBidRangePosition)}</strong>, Aufschlag{" "}
              <strong>{String(round.lockedSurchargePercent)} %</strong>
              {round.lockedSurchargeOnBids ? " auf die Gebote" : ""}
              {round.lockedSurchargeOnAverage ? " auf den Durchschnitt" : ""}.
            </p>
            <Button
              variant={"outline-dark"}
              disabled={busy}
              onClick={() =>
                runAction(
                  () => api.biddingRoundsApiUnlockAverageBidCreate({ roundId }),
                  "Durchschnittsgebot freigegeben",
                )
              }
            >
              Freigeben
            </Button>
          </>
        ) : (
          <>
            <Row className={"g-3 align-items-end"}>
              <Col md={6}>
                <Form.Label>Position: {lockPosition}</Form.Label>
                <Form.Range
                  min={0}
                  max={100}
                  step={10}
                  value={lockPosition}
                  onChange={(event) =>
                    setLockPosition(Number(event.target.value))
                  }
                />
              </Col>
              <Col md={2}>
                <Form.Label>Aufschlag %</Form.Label>
                <Form.Control
                  value={surchargePercent}
                  onChange={(event) => setSurchargePercent(event.target.value)}
                />
              </Col>
              <Col md={4}>
                <Form.Check
                  type={"checkbox"}
                  label={"Aufschlag auf die Gebote"}
                  checked={surchargeOnBids}
                  onChange={(event) => setSurchargeOnBids(event.target.checked)}
                />
                <Form.Check
                  type={"checkbox"}
                  label={"Aufschlag auf den Durchschnitt"}
                  checked={surchargeOnAverage}
                  onChange={(event) =>
                    setSurchargeOnAverage(event.target.checked)
                  }
                />
              </Col>
            </Row>
            <Button
              variant={"dark"}
              className={"mt-3"}
              disabled={busy}
              onClick={() =>
                runAction(
                  () =>
                    api.biddingRoundsApiLockAverageBidCreate({
                      roundId,
                      lockAverageBidRequest: {
                        position: lockPosition,
                        surchargePercent: Number(surchargePercent) || 0,
                        surchargeOnBids,
                        surchargeOnAverage,
                      },
                    }),
                  "Durchschnittsgebot fixiert",
                )
              }
            >
              Fixieren
            </Button>
          </>
        )}
      </Card.Body>
    </Card>
  );
};

export default LockAverageBidCard;
