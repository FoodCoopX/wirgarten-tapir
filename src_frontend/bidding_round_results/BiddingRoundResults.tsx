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
const LEVEL_KEYS = ["green", "yellow", "red"] as const;
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
  const [selectedLevel, setSelectedLevel] = useState<number>(1);
  const [createAutoRenewed, setCreateAutoRenewed] = useState<boolean>(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    void load();
  }, []);

  async function load(position?: number) {
    try {
      const [loadedRound, loadedResults] = await Promise.all([
        api.biddingRoundsApiRetrieve({ roundId }),
        api.biddingRoundsApiResultsRetrieve({ roundId, position }),
      ]);
      setRound(loadedRound);
      setResults(loadedResults);
      if (position === undefined) {
        setSelectedLevel(loadedResults.recommendedLevel);
      }
    } catch (error) {
      await handleRequestError(
        error,
        "Die Auswertung konnte nicht geladen werden.",
        setToastDatas,
      );
    } finally {
      setLoading(false);
    }
  }

  function selectLevel(level: number) {
    setSelectedLevel(level);
    void load((level - 1) * 50);
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
      await load((selectedLevel - 1) * 50);
    } catch (error) {
      await handleRequestError(
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

  const isBidRange = results.biddingProcedure === BID_RANGE_PROCEDURE;
  const levelCount = isBidRange
    ? 2
    : Math.min(Math.max(results.bidLevels, 1), 3);
  const levelKeys: Array<"green" | "yellow" | "red"> = isBidRange
    ? ["green", "red"]
    : [...LEVEL_KEYS].slice(0, levelCount);
  const levelLabels = isBidRange
    ? ["Grün", "Rot"]
    : ["Stufe 1", "Stufe 2", "Stufe 3"].slice(0, levelCount);
  const selectedLevelData =
    results.levels[levelKeys[selectedLevel - 1]] ?? results.levels.green;
  const coverage = selectedLevelData.coveragePercent;
  const coverageStatus = selectedLevelData.coverageStatus;
  const coverageStatusLabel =
    COVERAGE_STATUS_LABELS[coverageStatus] ?? coverageStatus;
  const selectedLevelLabel = levelLabels[selectedLevel - 1];

  return (
    <Container fluid className={"py-4"}>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />

      <div className={"d-flex justify-content-between align-items-center mb-4"}>
        <h1 className={"mb-0"}>{round.name}</h1>
        <div>
          <Badge bg={"secondary"} className={"me-2"}>
            {isBidRange ? "Gebotsspanne" : `Einfach, ${levelCount} Stufe(n)`}
          </Badge>
          <Badge bg={round.status === "active" ? "success" : "secondary"}>
            {round.status}
          </Badge>
        </div>
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
              <div className={"text-muted"}>
                Erreicht pro Jahr ({selectedLevelLabel})
              </div>
              <div className={"fs-4"}>
                {formatCurrency(Number(selectedLevelData.reachedPerYear))}
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
                Ø{" "}
                {formatCurrency(
                  Number(selectedLevelData.bidderAveragePerMonth),
                )}{" "}
                / Monat
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Card className={"mb-4"}>
        <Card.Body>
          <div className={"d-flex justify-content-between mb-1"}>
            <span>Deckung bei {selectedLevelLabel}</span>
            <strong>
              {coverage.toFixed(1)} %{" "}
              <Badge
                bg={COVERAGE_STATUS_VARIANTS[coverageStatus] ?? "secondary"}
              >
                {coverageStatusLabel}
              </Badge>
            </strong>
          </div>
          <ProgressBar
            now={Math.min(coverage, 100)}
            variant={COVERAGE_STATUS_VARIANTS[coverageStatus] ?? "secondary"}
          />
        </Card.Body>
      </Card>

      {levelCount > 1 && (
        <Card className={"mb-4"}>
          <Card.Header>
            <strong>Projektion je Stufe</strong>
          </Card.Header>
          <Card.Body>
            <Row className={"g-3"}>
              {levelLabels.map((label, index) => {
                const level = results.levels[levelKeys[index]];
                if (!level) {
                  return null;
                }
                const levelStatus = level.coverageStatus;
                return (
                  <Col md={4} key={label}>
                    <Card
                      className={
                        selectedLevel === index + 1
                          ? "border-dark h-100"
                          : "h-100"
                      }
                      role={"button"}
                      onClick={() => selectLevel(index + 1)}
                    >
                      <Card.Body>
                        <div className={"d-flex justify-content-between"}>
                          <strong>{label}</strong>
                          {results.recommendedLevel === index + 1 && (
                            <Badge bg={"dark"}>Empfohlen</Badge>
                          )}
                        </div>
                        <div className={"fs-4 mt-2"}>
                          {level.coveragePercent.toFixed(1)} %
                        </div>
                        <div className={"text-muted small"}>
                          {formatCurrency(Number(level.reachedPerYear))} pro
                          Jahr
                        </div>
                        <Badge
                          bg={
                            COVERAGE_STATUS_VARIANTS[levelStatus] ?? "secondary"
                          }
                          className={"mt-2"}
                        >
                          {COVERAGE_STATUS_LABELS[levelStatus] ?? levelStatus}
                        </Badge>
                      </Card.Body>
                    </Card>
                  </Col>
                );
              })}
            </Row>
          </Card.Body>
        </Card>
      )}

      <Card className={"mb-4"}>
        <Card.Header>
          <strong>Zusatzposten</strong>
        </Card.Header>
        <Card.Body>
          {Object.values(results.extraPositions).map((position) => (
            <div
              key={position.label}
              className={"d-flex justify-content-between"}
            >
              <span>{position.label}</span>
              <strong>
                {position.applicable
                  ? formatCurrency(Number(position.reachedPerYear))
                  : "–"}
              </strong>
            </div>
          ))}
        </Card.Body>
      </Card>

      <Card className={"mb-4"}>
        <Card.Header>
          <strong>
            Auto-Verlängerte ({results.autoRenewed.length}),{" "}
            {formatCurrency(Number(results.autoRenewedPerYear))} pro Jahr
          </strong>
        </Card.Header>
        <Card.Body className={"p-0"}>
          {results.autoRenewed.length === 0 ? (
            <Alert variant={"info"} className={"m-3"}>
              Keine automatisch verlängerten Mitglieder einbezogen.
            </Alert>
          ) : (
            <Table responsive hover className={"mb-0"}>
              <thead>
                <tr>
                  <th>Mitglied</th>
                  <th>Referenz / Monat</th>
                  <th>Referenz / Jahr</th>
                </tr>
              </thead>
              <tbody>
                {results.autoRenewed.map((entry) => (
                  <tr key={entry.memberId}>
                    <td>{entry.memberName}</td>
                    <td>{formatCurrency(Number(entry.monthlyReference))}</td>
                    <td>{formatCurrency(Number(entry.yearlyReference))}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
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
                  <th>Produkt</th>
                  <th>Anteile</th>
                  {levelLabels.map((label) => (
                    <th key={label}>{label}</th>
                  ))}
                  <th>Beitrag / Monat</th>
                  <th>Beitrag / Jahr</th>
                </tr>
              </thead>
              <tbody>
                {results.bids.map((bid) => {
                  const amounts = [bid.amount1, bid.amount2, bid.amount3];
                  return (
                    <tr key={bid.bidId}>
                      <td>{bid.memberName}</td>
                      <td>{bid.email}</td>
                      <td>{bid.productName}</td>
                      <td>{bid.quantity}</td>
                      {levelLabels.map((label, index) => (
                        <td key={label}>
                          {amounts[index]
                            ? formatCurrency(Number(amounts[index]))
                            : "–"}
                        </td>
                      ))}
                      <td>{formatCurrency(Number(bid.amountPerMonth))}</td>
                      <td>{formatCurrency(Number(bid.amountPerYear))}</td>
                    </tr>
                  );
                })}
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
          {round.contractsCreatedAt ? (
            <Alert variant={"success"}>
              Verträge erstellt am{" "}
              {new Date(round.contractsCreatedAt).toLocaleString("de-DE")}. Die
              Erzeugung ist endgültig; Korrekturen laufen über die normalen
              Verwaltungswerkzeuge.
            </Alert>
          ) : round.status !== "closed" ? (
            <Alert variant={"info"}>
              Verträge können erst erstellt werden, wenn die Beitragsrunde
              geschlossen ist.
            </Alert>
          ) : (
            <>
              {levelCount > 1 && (
                <Form.Group className={"mb-3"}>
                  <Form.Label>Gebotsstufe für die Verträge</Form.Label>
                  <Form.Select
                    value={String(selectedLevel)}
                    onChange={(event) =>
                      selectLevel(Number(event.target.value))
                    }
                  >
                    {levelLabels.map((label, index) => (
                      <option key={label} value={String(index + 1)}>
                        {label}
                      </option>
                    ))}
                  </Form.Select>
                  <Form.Text className={"text-muted"}>
                    Empfohlen: Stufe {results.recommendedLevel} bei{" "}
                    {coverage.toFixed(1)} % Deckung.
                  </Form.Text>
                </Form.Group>
              )}
              <Form.Check
                type={"checkbox"}
                className={"mb-3"}
                label={
                  "Verträge für automatisch verlängerte Mitglieder mit erzeugen"
                }
                checked={createAutoRenewed}
                onChange={(event) => setCreateAutoRenewed(event.target.checked)}
              />
              <Button
                variant={"dark"}
                disabled={busy || results.bids.length === 0}
                onClick={() =>
                  runAction(
                    () =>
                      api.biddingRoundsApiCreateContractsCreate({
                        roundId,
                        createContractsRequest: {
                          ...(levelCount > 1
                            ? { bidLevel: selectedLevel }
                            : {}),
                          createAutoRenewedContracts: createAutoRenewed,
                        },
                      }),
                    "Verträge erstellt",
                  )
                }
              >
                Verträge aus allen Geboten erstellen
              </Button>
            </>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default BiddingRoundResults;
