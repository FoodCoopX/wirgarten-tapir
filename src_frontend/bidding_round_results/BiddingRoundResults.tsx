import React, { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
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
import { handleRequestError } from "../utils/handleRequestError.ts";

interface BiddingRoundResultsProps {
  csrfToken: string;
}

const EURO_FORMAT = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
});

function getRoundIdFromPath(): string {
  const parts = window.location.pathname.split("/").filter(Boolean);
  const adminIndex = parts.indexOf("admin");
  return parts[adminIndex + 1] ?? "";
}

function getCoverageVariant(
  coverage: number,
): "success" | "warning" | "danger" {
  if (coverage >= 100) return "success";
  if (coverage >= 90) return "warning";
  return "danger";
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
      <Button
        variant={"dark"}
        disabled={busy || results.bids.length === 0}
        onClick={() =>
          runAction(
            () =>
              api.biddingRoundsApiCreateContractsCreate({
                roundId,
                createContractsRequest: {},
              }),
            "Verträge erstellt",
          )
        }
      >
        Verträge aus allen Geboten erstellen
      </Button>
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
                {EURO_FORMAT.format(Number(results.targetPerYear))}
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className={"h-100"}>
            <Card.Body>
              <div className={"text-muted"}>Erreicht pro Jahr</div>
              <div className={"fs-4"}>
                {EURO_FORMAT.format(Number(results.reachedPerYear))}
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
                Ø {EURO_FORMAT.format(Number(results.bidderAveragePerMonth))} /
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
            variant={getCoverageVariant(coverage)}
          />
        </Card.Body>
      </Card>

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
                    <td>{EURO_FORMAT.format(Number(bid.amountPerMonth))}</td>
                    <td>{EURO_FORMAT.format(Number(bid.amountPerYear))}</td>
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
