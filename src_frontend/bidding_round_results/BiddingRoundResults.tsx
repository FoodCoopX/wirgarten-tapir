import React, { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Form,
  Modal,
  ProgressBar,
  Row,
  Spinner,
  Table,
} from "react-bootstrap";

import { BiddingRoundsApi } from "../api-client/apis/BiddingRoundsApi.ts";
import { MemberOption } from "../api-client/models/MemberOption.ts";
import { Round } from "../api-client/models/Round.ts";
import { RoundResultsResponse } from "../api-client/models/RoundResultsResponse.ts";
import { RoundStatsBid } from "../api-client/models/RoundStatsBid.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "../utils/addToast.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

import ContractsCard from "./components/ContractsCard.tsx";
import LockAverageBidCard from "./components/LockAverageBidCard.tsx";

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

function buildItem(
  roundProductTypeId: string,
  productId: string,
  quantity: number,
  amounts: string[],
) {
  return {
    roundProductTypeId,
    productId,
    quantity,
    amount1: amounts[0] || null,
    amount2: amounts[1] || null,
    amount3: amounts[2] || null,
  };
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
  const [filter, setFilter] = useState<string>("all");
  const [sort, setSort] = useState<string>("name");
  const [lockPosition, setLockPosition] = useState<number>(50);
  const [surchargePercent, setSurchargePercent] = useState<string>("0");
  const [surchargeOnBids, setSurchargeOnBids] = useState<boolean>(false);
  const [surchargeOnAverage, setSurchargeOnAverage] = useState<boolean>(false);
  const [editingBid, setEditingBid] = useState<RoundStatsBid | null>(null);
  const [editAmounts, setEditAmounts] = useState<string[]>(["", "", ""]);
  const [editQuantity, setEditQuantity] = useState<number>(1);
  const [editConfirmed, setEditConfirmed] = useState<boolean>(true);
  const [showManualBid, setShowManualBid] = useState<boolean>(false);
  const [membersWithoutBid, setMembersWithoutBid] = useState<MemberOption[]>(
    [],
  );
  const [manualMemberId, setManualMemberId] = useState<string>("");
  const [manualProductId, setManualProductId] = useState<string>("");
  const [manualAmounts, setManualAmounts] = useState<string[]>(["", "", ""]);
  const [manualQuantity, setManualQuantity] = useState<number>(1);
  const [manualConfirmed, setManualConfirmed] = useState<boolean>(true);
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
      if (loadedRound.averageBidLockedAt) {
        setLockPosition(Number(loadedRound.lockedBidRangePosition ?? 50));
        setSurchargePercent(String(loadedRound.lockedSurchargePercent ?? "0"));
        setSurchargeOnBids(loadedRound.lockedSurchargeOnBids);
        setSurchargeOnAverage(loadedRound.lockedSurchargeOnAverage);
      } else {
        setLockPosition((loadedResults.recommendedLevel - 1) * 50);
      }
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
      handleRequestError(
        error,
        "Die Aktion ist fehlgeschlagen.",
        setToastDatas,
      );
    } finally {
      setBusy(false);
    }
  }

  async function openManualBid() {
    try {
      const members = await api.biddingRoundsApiMembersWithoutBidList({
        roundId,
      });
      setMembersWithoutBid(members);
      setManualMemberId(members[0]?.id ?? "");
      setManualProductId(round?.product?.prices?.[0]?.productId ?? "");
      setManualAmounts(["", "", ""]);
      setManualQuantity(1);
      setShowManualBid(true);
    } catch (error) {
      handleRequestError(
        error,
        "Die Mitglieder konnten nicht geladen werden.",
        setToastDatas,
      );
    }
  }

  function openEditBid(bid: RoundStatsBid) {
    setEditingBid(bid);
    setEditAmounts([
      bid.items[0]?.amount1 ?? "",
      bid.items[0]?.amount2 ?? "",
      bid.items[0]?.amount3 ?? "",
    ]);
    setEditQuantity(bid.items[0]?.quantity ?? 1);
    setEditConfirmed(!!bid.adminConfirmed);
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
  const isLocked = !!round.averageBidLockedAt;

  const visibleBids = [...results.bids]
    .filter((bid) => {
      if (filter === "confirmed") {
        return !!bid.adminConfirmed;
      }
      if (filter === "unconfirmed") {
        return !bid.adminConfirmed;
      }
      return true;
    })
    .sort((first, second) => {
      if (sort === "date") {
        return String(second.updatedAt).localeCompare(String(first.updatedAt));
      }
      return first.memberName.localeCompare(second.memberName, "de");
    });

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
          {isLocked && (
            <Badge bg={"dark"} className={"ms-2"}>
              Gebot fixiert
            </Badge>
          )}
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

      <LockAverageBidCard
        round={round}
        isLocked={isLocked}
        busy={busy}
        api={api}
        roundId={roundId}
        runAction={runAction}
        lockPosition={lockPosition}
        setLockPosition={setLockPosition}
        surchargePercent={surchargePercent}
        setSurchargePercent={setSurchargePercent}
        surchargeOnBids={surchargeOnBids}
        setSurchargeOnBids={setSurchargeOnBids}
        surchargeOnAverage={surchargeOnAverage}
        setSurchargeOnAverage={setSurchargeOnAverage}
      />

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
          <div className={"d-flex flex-wrap gap-2 align-items-center"}>
            <strong className={"me-auto"}>Gebote</strong>
            <Form.Select
              size={"sm"}
              style={{ width: "auto" }}
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value={"all"}>Alle</option>
              <option value={"confirmed"}>Bestätigt</option>
              <option value={"unconfirmed"}>
                Unbestätigt ({results.unconfirmedBidCount})
              </option>
            </Form.Select>
            <Form.Select
              size={"sm"}
              style={{ width: "auto" }}
              value={sort}
              onChange={(event) => setSort(event.target.value)}
            >
              <option value={"name"}>Name</option>
              <option value={"date"}>Datum</option>
            </Form.Select>
            <Button
              size={"sm"}
              variant={"outline-dark"}
              disabled={busy || results.unconfirmedBidCount === 0}
              onClick={() =>
                runAction(
                  () =>
                    api.biddingRoundsApiConfirmBidsCreate({
                      roundId,
                      confirmBidsRequest: {},
                    }),
                  "Alle Gebote bestätigt",
                )
              }
            >
              Alle bestätigen
            </Button>
            <Button
              size={"sm"}
              variant={"dark"}
              onClick={openManualBid}
              disabled={busy}
            >
              Manuelles Gebot
            </Button>
            <Button
              size={"sm"}
              variant={"outline-dark"}
              href={`/bidding_rounds/api/${roundId}/export.csv`}
            >
              CSV
            </Button>
          </div>
        </Card.Header>
        <Card.Body className={"p-0"}>
          {visibleBids.length === 0 ? (
            <Alert variant={"info"} className={"m-3"}>
              Keine Gebote für diesen Filter.
            </Alert>
          ) : (
            <Table responsive hover className={"mb-0"}>
              <thead>
                <tr>
                  <th>Mitglied</th>
                  <th>E-Mail</th>
                  <th>Anteile</th>
                  {levelLabels.map((label) => (
                    <th key={label}>{label}</th>
                  ))}
                  <th>Gewählt / Monat</th>
                  <th>Bestätigt</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {visibleBids.map((bid) => {
                  const amounts = [
                    bid.items[0]?.amount1,
                    bid.items[0]?.amount2,
                    bid.items[0]?.amount3,
                  ];
                  return (
                    <tr key={bid.bidId}>
                      <td>
                        {bid.memberName}
                        {bid.enteredByAdmin && (
                          <Badge bg={"secondary"} className={"ms-2"}>
                            Admin
                          </Badge>
                        )}
                      </td>
                      <td>{bid.email}</td>
                      <td>
                        {bid.items.reduce(
                          (total, item) => total + item.quantity,
                          0,
                        )}
                      </td>
                      {levelLabels.map((label, index) => (
                        <td key={label}>
                          {amounts[index]
                            ? formatCurrency(Number(amounts[index]))
                            : "–"}
                        </td>
                      ))}
                      <td>{formatCurrency(Number(bid.amountPerMonth))}</td>
                      <td>
                        {bid.adminConfirmed ? (
                          <Badge bg={"success"}>ja</Badge>
                        ) : (
                          <Badge bg={"warning"}>nein</Badge>
                        )}
                      </td>
                      <td>
                        <div className={"d-flex gap-1"}>
                          <Button
                            size={"sm"}
                            variant={"outline-dark"}
                            onClick={() => openEditBid(bid)}
                          >
                            Bearbeiten
                          </Button>
                          <Button
                            size={"sm"}
                            variant={"outline-danger"}
                            disabled={busy}
                            onClick={() =>
                              runAction(
                                () =>
                                  api.biddingRoundsApiBidsDestroy({
                                    roundId,
                                    bidId: bid.bidId,
                                  }),
                                "Gebot gelöscht",
                              )
                            }
                          >
                            Löschen
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      <ContractsCard
        round={round}
        results={results}
        isLocked={isLocked}
        busy={busy}
        createAutoRenewed={createAutoRenewed}
        setCreateAutoRenewed={setCreateAutoRenewed}
        api={api}
        roundId={roundId}
        runAction={runAction}
      />

      <Modal show={!!editingBid} onHide={() => setEditingBid(null)}>
        <Modal.Header closeButton>
          <Modal.Title>Gebot bearbeiten</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {editingBid && (
            <>
              <p className={"text-muted"}>{editingBid.memberName}</p>
              <Form.Group className={"mb-3"}>
                <Form.Label>Anteile</Form.Label>
                <Form.Control
                  type={"number"}
                  min={1}
                  max={5}
                  value={editQuantity}
                  onChange={(event) =>
                    setEditQuantity(Number(event.target.value))
                  }
                />
              </Form.Group>
              {levelLabels.map((label, index) => (
                <Form.Group key={label} className={"mb-3"}>
                  <Form.Label>{label}</Form.Label>
                  <Form.Control
                    value={editAmounts[index]}
                    onChange={(event) => {
                      const next = [...editAmounts];
                      next[index] = event.target.value;
                      setEditAmounts(next);
                    }}
                  />
                </Form.Group>
              ))}
              <Form.Check
                type={"checkbox"}
                label={"Bestätigt"}
                checked={editConfirmed}
                onChange={(event) => setEditConfirmed(event.target.checked)}
              />
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant={"outline-dark"} onClick={() => setEditingBid(null)}>
            Abbrechen
          </Button>
          <Button
            variant={"dark"}
            disabled={busy || !results.roundProductTypeId}
            onClick={() =>
              runAction(
                () =>
                  api.biddingRoundsApiBidsPartialUpdate({
                    roundId,
                    bidId: editingBid!.bidId,
                    patchedBidAdminRequest: {
                      items: [
                        buildItem(
                          results.roundProductTypeId!,
                          editingBid!.items[0].productId,
                          editQuantity,
                          editAmounts,
                        ),
                      ],
                      adminConfirmed: editConfirmed,
                    },
                  }),
                "Gebot gespeichert",
              ).then(() => setEditingBid(null))
            }
          >
            Speichern
          </Button>
        </Modal.Footer>
      </Modal>

      <Modal show={showManualBid} onHide={() => setShowManualBid(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Manuelles Gebot</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group className={"mb-3"}>
            <Form.Label>Mitglied</Form.Label>
            <Form.Select
              value={manualMemberId}
              onChange={(event) => setManualMemberId(event.target.value)}
            >
              {membersWithoutBid.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.name} ({member.email})
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group className={"mb-3"}>
            <Form.Label>Produkt</Form.Label>
            <Form.Select
              value={manualProductId}
              onChange={(event) => setManualProductId(event.target.value)}
            >
              {(round.product?.prices ?? []).map((price) => (
                <option key={price.productId} value={price.productId}>
                  {price.productName}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group className={"mb-3"}>
            <Form.Label>Anteile</Form.Label>
            <Form.Control
              type={"number"}
              min={1}
              max={5}
              value={manualQuantity}
              onChange={(event) =>
                setManualQuantity(Number(event.target.value))
              }
            />
          </Form.Group>
          {levelLabels.map((label, index) => (
            <Form.Group key={label} className={"mb-3"}>
              <Form.Label>{label}</Form.Label>
              <Form.Control
                value={manualAmounts[index]}
                onChange={(event) => {
                  const next = [...manualAmounts];
                  next[index] = event.target.value;
                  setManualAmounts(next);
                }}
              />
            </Form.Group>
          ))}
          <Form.Check
            type={"checkbox"}
            label={"Bestätigt"}
            checked={manualConfirmed}
            onChange={(event) => setManualConfirmed(event.target.checked)}
          />
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant={"outline-dark"}
            onClick={() => setShowManualBid(false)}
          >
            Abbrechen
          </Button>
          <Button
            variant={"dark"}
            disabled={busy || !manualMemberId || !results.roundProductTypeId}
            onClick={() =>
              runAction(
                () =>
                  api.biddingRoundsApiBidsCreate({
                    roundId,
                    bidAdminCreateRequest: {
                      memberId: manualMemberId,
                      items: [
                        buildItem(
                          results.roundProductTypeId!,
                          manualProductId,
                          manualQuantity,
                          manualAmounts,
                        ),
                      ],
                      enteredByAdmin: true,
                      adminConfirmed: manualConfirmed,
                    },
                  }),
                "Gebot angelegt",
              ).then(() => setShowManualBid(false))
            }
          >
            Speichern
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default BiddingRoundResults;
