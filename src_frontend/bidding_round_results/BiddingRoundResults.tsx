import React, { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Form,
  ProgressBar,
  Row,
  Spinner,
  Table,
} from "react-bootstrap";

import { BiddingRoundsApi } from "../api-client/apis/BiddingRoundsApi.ts";
import { Round } from "../api-client/models/Round.ts";
import { RoundResultsResponse } from "../api-client/models/RoundResultsResponse.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "../utils/addToast.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface BiddingRoundResultsProps {
  csrfToken: string;
}

const BID_RANGE_PROCEDURE = "bid_range";
const COVERAGE_STATUS_LABELS: Record<string, string> = {
  green: "Grün",
  yellow: "Gelb",
  red: "Rot",
};
const COVERAGE_STATUS_VARIANTS: Record<string, string> = {
  green: "success",
  yellow: "warning",
  red: "danger",
};

function getRoundIdFromPath(): string {
  const parts = window.location.pathname.split("/").filter(Boolean);
  const adminIndex = parts.indexOf("admin");
  return parts[adminIndex + 1] ?? "";
}

const BiddingRoundResults: React.FC<BiddingRoundResultsProps> = ({
  csrfToken,
}) => {
  const api = useApi(BiddingRoundsApi, csrfToken);
  const roundId = getRoundIdFromPath();
  const [round, setRound] = useState<Round | null>(null);
  const [results, setResults] = useState<RoundResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState(2);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const [loadedRound, loadedResults] = await Promise.all([
        api.biddingRoundsApiRetrieve({ roundId }),
        api.biddingRoundsApiResultsRetrieve({ roundId }),
      ]);
      setRound(loadedRound);
      setResults(loadedResults);
      setSelectedLevel(loadedResults.recommendedLevel);
    } catch (error) {
      handleRequestError(
        error,
        "Die Auswertung konnte nicht geladen werden.",
        setToastDatas,
      );
    } finally {
      setLoading(false);
    }
  }

  async function runAction(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    try {
      await action();
      addToast(
        {
          title: message,
          variant: "success",
          id: crypto.randomUUID(),
        },
        setToastDatas,
      );
      await load();
    } catch (error) {
      handleRequestError(
        error,
        "Die Aktion ist fehlgeschlagen.",
        setToastDatas,
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <Container className={"py-5 text-center"}>
        <Spinner animation={"border"} />
      </Container>
    );
  }

  if (!round || !results) {
    return (
      <Container className={"py-5"}>
        <Alert variant={"danger"}>
          Die Beitragsrunde konnte nicht geladen werden.
        </Alert>
      </Container>
    );
  }

  const coverage = Math.min(Math.round(results.coveragePercent), 100);
  const isBidRange = results.biddingProcedure === BID_RANGE_PROCEDURE;
  function renderContractsSection() {
    if (round.contractsCreatedAt) {
      return (
        <Alert variant={"success"}>
          Verträge erstellt am{" "}
          {new Date(round.contractsCreatedAt).toLocaleString("de-DE")}. Die
          Erzeugung ist endgültig; Korrekturen laufen über die normalen
          Verwaltungswerkzeuge.
        </Alert>
      );
    }
    if (round.status !== "closed") {
      return (
        <Alert variant={"info"}>
          Verträge können erst erstellt werden, wenn die Beitragsrunde
          geschlossen ist.
        </Alert>
      );
    }
    return (
      <>
        {isBidRange && (
          <Form.Group className={"mb-3"}>
            <Form.Label>Gebotsstufe für die Verträge</Form.Label>
            <Form.Select
              value={String(selectedLevel)}
              onChange={(event) => setSelectedLevel(Number(event.target.value))}
            >
              <option value={"1"}>Grün (Wunsch)</option>
              <option value={"2"}>Rot (Schmerzgrenze)</option>
            </Form.Select>
            <Form.Text className={"text-muted"}>
              Empfohlen: Stufe {results.recommendedLevel} bei{" "}
              {results.coveragePercent.toFixed(1)} % Deckung.
            </Form.Text>
          </Form.Group>
        )}
        <Button
          variant={"dark"}
          disabled={busy || results.bids.length === 0}
          onClick={() =>
            runAction(
              () =>
                api.biddingRoundsApiCreateContractsCreate({
                  roundId,
                  createContractsRequest: isBidRange
                    ? { bidLevel: selectedLevel }
                    : {},
                }),
              "Verträge erstellt",
            )
          }
        >
          Verträge aus allen Geboten erstellen
        </Button>
      </>
    );
  }

  return (
    <Container fluid className={"py-4"}>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />

      <div className={"d-flex justify-content-between align-items-center mb-4"}>
        <h1 className={"mb-0"}>{round.name}</h1>
        <Badge bg={round.status === "active" ? "success" : "secondary"}>
          {round.status}
        </Badge>
      </div>

      <Row className={"g-3 mb-4"}>
        <Col md={4}>
          <Card className={"h-100"}>
            <Card.Body>
              <div className={"text-muted"}>Ziel pro Jahr</div>
              <div className={"fs-4"}>
                {formatCurrency(Number(results.targetPerYear))}
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className={"h-100"}>
            <Card.Body>
              <div className={"text-muted"}>Erreicht pro Jahr</div>
              <div className={"fs-4"}>
                {formatCurrency(Number(results.reachedPerYear))}
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className={"h-100"}>
            <Card.Body>
              <div className={"text-muted"}>Bietende</div>
              <div className={"fs-4"}>{results.bidderCount}</div>
              <div className={"text-muted small"}>
                Ø {formatCurrency(Number(results.bidderAveragePerMonth))} /
                Monat
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Card className={"mb-4"}>
        <Card.Body>
          <div className={"d-flex justify-content-between mb-1"}>
            <span>Deckung</span>
            <strong>{results.coveragePercent.toFixed(1)} %</strong>
          </div>
          <ProgressBar
            now={coverage}
            variant={
              COVERAGE_STATUS_VARIANTS[results.coverageStatus] ?? "secondary"
            }
          />
        </Card.Body>
      </Card>

      {isBidRange && (
        <Card className={"mb-4"}>
          <Card.Header>
            <strong>Gebotsstufen</strong>
            <Badge
              bg={
                COVERAGE_STATUS_VARIANTS[results.coverageStatus] ?? "secondary"
              }
              className={"ms-2"}
            >
              {COVERAGE_STATUS_LABELS[results.coverageStatus] ??
                results.coverageStatus}
            </Badge>
          </Card.Header>
          <Card.Body className={"p-0"}>
            <Table responsive size={"sm"} className={"mb-0"}>
              <thead>
                <tr>
                  <th>Stufe</th>
                  <th>Erreicht pro Jahr</th>
                  <th>Deckung</th>
                  <th>Bietende Ø / Monat</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["green", "Grün", results.levels.green],
                    ["red", "Rot", results.levels.red],
                  ] as const
                ).map(([key, label, level]) => (
                  <tr key={key}>
                    <td>{label}</td>
                    <td>{formatCurrency(Number(level.reachedPerYear))}</td>
                    <td>{level.coveragePercent.toFixed(1)} %</td>
                    <td>
                      {formatCurrency(Number(level.bidderAveragePerMonth))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card.Body>
        </Card>
      )}

      <Card className={"mb-4"}>
        <Card.Header>
          <strong>Gebote</strong>
        </Card.Header>
        <Card.Body className={"p-0"}>
          {results.bids.length === 0 ? (
            <Alert variant={"info"} className={"m-3"}>
              Noch keine Gebote abgegeben.
            </Alert>
          ) : (
            <Table responsive hover className={"mb-0"}>
              <thead>
                <tr>
                  <th>Mitglied</th>
                  <th>E-Mail</th>
                  <th>Anteile</th>
                  <th>Beitrag / Monat</th>
                  <th>Beitrag / Jahr</th>
                </tr>
              </thead>
              <tbody>
                {results.bids.map((bid) => (
                  <tr key={bid.bidId}>
                    <td>{bid.memberName}</td>
                    <td>{bid.email}</td>
                    <td>
                      {bid.items.reduce(
                        (total, item) => total + item.quantity,
                        0,
                      )}
                    </td>
                    <td>{formatCurrency(Number(bid.amountPerMonth))}</td>
                    <td>{formatCurrency(Number(bid.amountPerYear))}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          <strong>Verträge</strong>
        </Card.Header>
        <Card.Body>
          {renderContractsSection()}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default BiddingRoundResults;
