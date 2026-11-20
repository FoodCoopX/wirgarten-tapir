import React, { useState } from "react";
import { Alert, Badge, Button, Card, Form } from "react-bootstrap";

import type { FinancingProjection } from "../../api-client/models/FinancingProjection.ts";
import type { RoundResultsResponse } from "../../api-client/models/RoundResultsResponse.ts";
import { applyDisplayName } from "../../bidding_round/utils/applyDisplayName.ts";
import DeckungAuslastungBars from "../../components/DeckungAuslastungBars.tsx";
import { interpolate } from "../../utils/interpolate.ts";
import {
  formatEuro,
  formatNumber,
  levelFromPosition,
} from "../../utils/resultsFormat.ts";
import type { CoverageTarget, TwelveMonthProjection } from "../types.ts";
import type { FinancingProjectionResult } from "../utils/financingProjection.ts";
import ExampleBidsTable from "./ExampleBidsTable.tsx";
import FinancingBreakdownTable from "./FinancingBreakdownTable.tsx";
import FinancingFormulaDetails from "./FinancingFormulaDetails.tsx";
import FinancingSurchargePanel from "./FinancingSurchargePanel.tsx";
import TwelveMonthProjectionChart from "./TwelveMonthProjectionChart.tsx";

interface FinancingProjectionCardProps {
  data: RoundResultsResponse;
  displayName: string;
  isBidRange: boolean;
  bidLevels: number;
  recommendedLevel: number;
  bidRangePosition: number;
  onBidRangePositionChange: (position: number) => void;
  includeAutoRenewed: boolean;
  onIncludeAutoRenewedChange: (enabled: boolean) => void;
  surchargePercent: number;
  onSurchargePercentChange: (percent: number) => void;
  surchargeOnBids: boolean;
  onSurchargeOnBidsChange: (enabled: boolean) => void;
  surchargeOnAverage: boolean;
  onSurchargeOnAverageChange: (enabled: boolean) => void;
  surchargeFactor: number;
  membershipIncludedInProductType: boolean;
  membershipFeesApply: boolean;
  financingProjection: FinancingProjection;
  dynamicProjection: FinancingProjectionResult;
  coverageTarget: CoverageTarget | null;
  onGoToCoverageTarget: () => void;
  averageBidLocked: boolean;
  contractsCreatedAt: string | null;
  onLockAverageBid: () => void;
  onUnlockAverageBid: () => void;
  twelveMonthProjection: TwelveMonthProjection | null;
  showProjection: boolean;
  onToggleProjection: () => void;
  newMembersPerMonth: number;
  onNewMembersPerMonthChange: (membersPerMonth: number) => void;
}

function bidLevelHint(isBidRange: boolean, bidLevels: number): string {
  if (isBidRange) {
    return " — auf dem gewählten Niveau";
  }
  if (bidLevels > 1) {
    return " — auf der gewählten Stufe";
  }
  return "";
}

function lockedSurchargeScopeLabel(
  onBids: boolean | undefined,
  onAverage: boolean | undefined,
): string {
  if (onBids && onAverage) {
    return "auf Gebote und Durchschnittsgebot";
  }
  if (onBids) {
    return "auf Gebote";
  }
  if (onAverage) {
    return "auf Durchschnittsgebot";
  }
  return "inaktiv";
}

interface FinancingIntroProps {
  isBidRange: boolean;
  bidLevels: number;
  displayName: string;
}

const FinancingIntro: React.FC<FinancingIntroProps> = ({
  isBidRange,
  bidLevels,
  displayName,
}) => {
  if (isBidRange) {
    return (
      <>
        <p className="text-muted mt-2 mb-1">
          {"Der Regler ist das"}{" "}
          <strong>{"gewählte Solidaritätsniveau"}</strong>
          {": eine Skala von"} <em>{"Grün (0, Wunsch)"}</em> {"bis"}{" "}
          <em>{"Rot (100, Schmerzgrenze)"}</em>
          {". Zu jedem Gebot gehören zwei Beträge —"}{" "}
          <em>{"Wunsch (Grün)"}</em> {"und"}{" "}
          <em>{"Schmerzgrenze (Rot)"}</em>
          {
            ". Die Regler-Position legt fest, mit welchem dieser Beträge gerechnet wird (dazwischen stufenlos interpoliert)."
          }
        </p>
        <p className="text-muted small mb-2">
          <strong>{"Warum solidarisch?"}</strong>{" "}
          {"Je weiter der Regler in Richtung"} <em>{"Rot"}</em>
          {
            ", desto mehr zahlen die Bietenden (bis zur Schmerzgrenze) und desto stärker tragen sie den Bedarf mit — dadurch"
          }{" "}
          <strong>{"sinkt"}</strong>{" "}
          {
            "das Durchschnittsgebot für alle, die nicht geboten haben. In Richtung"
          }{" "}
          <em>{"Grün"}</em>{" "}
          {
            "zahlen die Bietenden nur ihren Wunsch, dann übernehmen die übrigen mehr. In beiden Fällen bleibt das Ziel bei voller Auslastung gedeckt."
          }
        </p>
      </>
    );
  }
  return (
    <p className="text-muted mt-2 mb-2">
      {bidLevels > 1 ? (
        <>
          {interpolate(
            "Jedes Gebot hat mehrere Beträge (Gebot 1 bis Gebot {count}).",
            { count: bidLevels },
          )}{" "}
          {
            "Gebot 1 ist der Wunschbetrag; reicht er nicht, gilt automatisch die nächste Stufe. Die Bietenden zahlen den Betrag der gültigen Stufe; alle, die nicht geboten haben — Auto-Verlängerer und Mitglieder, die nach der"
          }{" "}
          {applyDisplayName("Beitragsrunde", displayName)}{" "}
          {"— zahlen dasselbe"}{" "}
          <strong>{"dynamische Durchschnittsgebot"}</strong>
          {
            ". Es ist so berechnet, dass bei voller Auslastung der Ziel-Deckungsbetrag gedeckt ist."
          }
        </>
      ) : (
        <>
          {
            "Jedes Gebot hat genau einen Betrag. Die Bietenden zahlen diesen Betrag; alle, die nicht geboten haben — Auto-Verlängerer und Mitglieder, die nach der"
          }{" "}
          {applyDisplayName("Beitragsrunde", displayName)}{" "}
          {"— zahlen dasselbe"}{" "}
          <strong>{"dynamische Durchschnittsgebot"}</strong>
          {
            ". Es ist so berechnet, dass bei voller Auslastung der Ziel-Deckungsbetrag gedeckt ist."
          }
        </>
      )}
    </p>
  );
};

const FinancingProjectionCard: React.FC<FinancingProjectionCardProps> = ({
  data,
  displayName,
  isBidRange,
  bidLevels,
  recommendedLevel,
  bidRangePosition,
  onBidRangePositionChange,
  includeAutoRenewed,
  onIncludeAutoRenewedChange,
  surchargePercent,
  onSurchargePercentChange,
  surchargeOnBids,
  onSurchargeOnBidsChange,
  surchargeOnAverage,
  onSurchargeOnAverageChange,
  surchargeFactor,
  membershipIncludedInProductType,
  membershipFeesApply,
  financingProjection,
  dynamicProjection,
  coverageTarget,
  onGoToCoverageTarget,
  averageBidLocked,
  contractsCreatedAt,
  onLockAverageBid,
  onUnlockAverageBid,
  twelveMonthProjection,
  showProjection,
  onToggleProjection,
  newMembersPerMonth,
  onNewMembersPerMonthChange,
}) => {
  const [showFormula, setShowFormula] = useState(false);
  const [showSurcharge, setShowSurcharge] = useState(false);
  const [showExample, setShowExample] = useState(false);

  return (
    <Card className="mb-4">
      <Card.Body>
        <div className="d-flex flex-row justify-content-between align-items-center">
          <div>
            <Card.Title className="mb-0">
              {isBidRange
                ? "Finanzierung & dynamisches Durchschnittsgebot"
                : "Finanzierung & Durchschnittsgebot"}
            </Card.Title>
            <div className="text-muted small">
              {"Was-wäre-wenn (zielgedeckter Durchschnitt)"}
            </div>
          </div>
          <Form.Check
            type="switch"
            label={"Auto-Verlängerung berücksichtigen"}
            checked={includeAutoRenewed}
            onChange={(event) =>
              onIncludeAutoRenewedChange(event.target.checked)
            }
          />
        </div>
        <FinancingIntro
          isBidRange={isBidRange}
          bidLevels={bidLevels}
          displayName={displayName}
        />
        <div className="mt-1 mb-2">
          <Button
            variant="link"
            className="p-0 small"
            onClick={() => setShowFormula(!showFormula)}
          >
            {showFormula
              ? "Wie wird gerechnet? ausblenden"
              : "Wie wird gerechnet?"}
          </Button>
          <FinancingFormulaDetails
            show={showFormula}
            isBidRange={isBidRange}
            bidLevels={bidLevels}
            membershipIncludedInProductType={membershipIncludedInProductType}
            membershipFeesApply={membershipFeesApply}
          />
        </div>
        <ul className="text-muted small mb-3">
          <li>
            <strong>{"Bietende Mitglieder"}</strong>{" "}
            {"zahlen ihr abgegebenes Gebot"}
            {bidLevelHint(isBidRange, bidLevels)}{" "}
            {"im Ø"}{" "}
            <strong>
              {formatEuro(dynamicProjection.bidderAveragePerMonth)}
            </strong>{" "}
            {"/ Anteil / Monat."}
          </li>
          <li>
            <strong>{"Alle, die nicht geboten haben"}</strong>{" "}
            {"— Auto-Verlängerer und Mitglieder, die nach der"}{" "}
            {applyDisplayName("Beitragsrunde", displayName)}{" "}
            {"— zahlen dasselbe"}{" "}
            <strong>{"dynamische Durchschnittsgebot"}</strong>{" "}
            <strong>
              {formatEuro(dynamicProjection.averagePerSharePerMonth)}
            </strong>{" "}
            {interpolate(
              "/ Anteil / Monat. Es ist so berechnet, dass bei voller Auslastung ({capacity} Anteile) der Ziel-Deckungsbetrag ({target}) gedeckt ist.",
              {
                capacity: formatNumber(financingProjection.capacityShares),
                target: formatEuro(dynamicProjection.target),
              },
            )}
          </li>
          {isBidRange && (
            <li>
              {"Regler nach"} <em>{"Grün"}</em>{" "}
              {"→ Bietende zahlen weniger ⇒ das Durchschnittsgebot"}{" "}
              <strong>{"steigt"}</strong>
              {"; Regler nach"} <em>{"Rot"}</em>{" "}
              {"→ Bietende zahlen mehr ⇒ das Durchschnittsgebot"}{" "}
              <strong>{"sinkt"}</strong>.
            </li>
          )}
        </ul>

        {isBidRange && (
          <>
            <div className="position-relative">
              <div
                style={{
                  height: "0.5rem",
                  borderRadius: "0.25rem",
                  background:
                    "linear-gradient(90deg, #198754 0%, #dc3545 100%)",
                  opacity: 0.5,
                }}
              />
              <Form.Range
                min={0}
                max={100}
                step={1}
                value={bidRangePosition}
                onChange={(event) =>
                  onBidRangePositionChange(Number(event.target.value))
                }
                disabled={averageBidLocked}
                className="w-100"
                style={{ marginTop: "-0.95rem" }}
                aria-label={"Solidaritätsniveau"}
              />
            </div>
            <div className="d-flex justify-content-between small text-muted">
              <span>{"Grün (Wunsch)"}</span>
              <span>{"Rot (Schmerzgrenze)"}</span>
            </div>
          </>
        )}
        {!isBidRange && bidLevels > 1 && (
          <>
            <p className="text-muted small mb-1">
              {"Empfohlene Stufe:"}{" "}
              <strong>
                {interpolate("Gebot {level}", {
                  level: recommendedLevel,
                })}
              </strong>{" "}
              {"(erste Stufe mit mindestens 90 % Deckung)."}
            </p>
            <Form.Range
              min={1}
              max={bidLevels}
              step={1}
              value={levelFromPosition(bidRangePosition, bidLevels)}
              onChange={(event) =>
                onBidRangePositionChange((Number(event.target.value) - 1) * 50)
              }
              disabled={averageBidLocked}
              className="w-100"
              aria-label={"Gebotsstufe"}
            />
            <div className="d-flex justify-content-between small text-muted">
              {Array.from({ length: bidLevels }, (_, i) => i + 1).map(
                (level) => (
                  <span key={level}>
                    {interpolate("Gebot {level}", { level })}
                    {level === recommendedLevel ? " (empfohlen)" : ""}
                  </span>
                ),
              )}
            </div>
          </>
        )}

        <div className="row mt-3 align-items-center">
          <div className="col-md-6">
            <div className="display-6">
              {formatEuro(dynamicProjection.bidderAveragePerMonth)}
            </div>
            <div>
              <span className="text-muted small">
                {"/ Anteil / Monat für"}{" "}
              </span>
              <span className="fw-bold fs-5">{"Bietende Ø"}</span>
            </div>
            <div className="text-muted small mb-2">
              = {formatEuro(dynamicProjection.bidderAveragePerMonth * 12)}{" "}
              {"/ Anteil / Jahr Ø"}
            </div>
            <div className="display-6">
              {formatEuro(dynamicProjection.averagePerSharePerMonth)}
            </div>
            <div>
              <span className="text-muted small">
                {"/ Anteil / Monat für"}{" "}
              </span>
              <span className="fw-bold fs-5">{"Nicht-Bietende"}</span>
            </div>
            <div className="text-muted small">
              = {formatEuro(dynamicProjection.averagePerSharePerMonth * 12)}{" "}
              {"/ Anteil / Jahr"}
            </div>
            <div className="text-muted small">
              {"tatsächlicher Nichtbieter-Satz: "}
              {formatEuro(data.nonBidderRatePerShare)} {"/ Anteil / Monat"}
            </div>
          </div>
          <div className="col-md-6">
            <DeckungAuslastungBars
              utilization={dynamicProjection.utilization}
              currentShares={dynamicProjection.currentShares}
              capacityShares={dynamicProjection.capacityShares}
              currentCoverage={dynamicProjection.currentCoverage}
              currentTotal={dynamicProjection.currentTotal}
              target={dynamicProjection.target}
              fullCoverage={dynamicProjection.coverage}
              fullTotal={dynamicProjection.total}
            />
          </div>
        </div>

        <div className="mt-3">
          <Button
            variant="link"
            className="p-0"
            onClick={() => setShowSurcharge(!showSurcharge)}
          >
            {showSurcharge ? "Aufschlag ausblenden" : "Aufschlag anzeigen"}
          </Button>
          <FinancingSurchargePanel
            show={showSurcharge}
            isBidRange={isBidRange}
            surchargePercent={surchargePercent}
            onSurchargePercentChange={onSurchargePercentChange}
            surchargeOnBids={surchargeOnBids}
            onSurchargeOnBidsChange={onSurchargeOnBidsChange}
            surchargeOnAverage={surchargeOnAverage}
            onSurchargeOnAverageChange={onSurchargeOnAverageChange}
            averageBidLocked={averageBidLocked}
            currentCoverage={dynamicProjection.currentCoverage}
          />
        </div>

        <div className="mt-3 d-flex align-items-center gap-2 flex-wrap">
          <Button
            variant="primary"
            onClick={onLockAverageBid}
            disabled={averageBidLocked}
          >
            {"Durchschnittsgebot festlegen"}
          </Button>
          <Button
            variant="outline-secondary"
            onClick={onUnlockAverageBid}
            disabled={!averageBidLocked || contractsCreatedAt != null}
          >
            {"Sperre aufheben"}
          </Button>
          {isBidRange && (
            <Button
              variant="outline-primary"
              onClick={onGoToCoverageTarget}
              disabled={averageBidLocked || !coverageTarget}
            >
              {"Ziel decken"}
            </Button>
          )}
          {isBidRange &&
            coverageTarget?.position === 100 &&
            !coverageTarget?.targetCovered && (
              <Alert variant="warning" className="mb-0 py-1">
                {"Das Ziel ist auch mit dem roten Betrag nicht gedeckt."}
              </Alert>
            )}
          {averageBidLocked && (
            <div className="p-2 bg-light rounded small">
              <strong>{"Gesperrtes Durchschnittsgebot"}</strong>
              {": "}
              {interpolate("Bietende {amount} / Anteil / Monat", {
                amount: formatEuro(
                  Number(data.averageBid.amountPerSharePerMonth ?? 0),
                ),
              })}
              {" · "}
              {interpolate("Nicht-Bietende {amount} / Anteil / Monat", {
                amount: formatEuro(dynamicProjection.averagePerSharePerMonth),
              })}
              {" · "}
              {interpolate("Aufschlag {percent} %", {
                percent: Number(data.lockedSurchargePercent ?? 0),
              })}
              {" ("}
              {lockedSurchargeScopeLabel(
                data.lockedSurchargeOnBids,
                data.lockedSurchargeOnAverage,
              )}
              {")"}
            </div>
          )}
          {contractsCreatedAt != null && (
            <Badge bg="warning" text="dark">
              {"Verträge erzeugt"}
            </Badge>
          )}
        </div>

        <FinancingBreakdownTable
          isBidRange={isBidRange}
          bidRangePosition={bidRangePosition}
          bidLevels={bidLevels}
          includeAutoRenewed={includeAutoRenewed}
          financingProjection={financingProjection}
          dynamicProjection={dynamicProjection}
          surchargePercent={surchargePercent}
          surchargeOnBids={surchargeOnBids}
          surchargeOnAverage={surchargeOnAverage}
        />

        <ExampleBidsTable
          isBidRange={isBidRange}
          bidRangePosition={bidRangePosition}
          surchargeOnBids={surchargeOnBids}
          surchargePercent={surchargePercent}
          surchargeFactor={surchargeFactor}
          showExample={showExample}
          onToggle={() => setShowExample(!showExample)}
        />

        <TwelveMonthProjectionChart
          show={showProjection}
          onToggle={onToggleProjection}
          projection={twelveMonthProjection}
          newMembersPerMonth={newMembersPerMonth}
          onNewMembersPerMonthChange={onNewMembersPerMonthChange}
        />
      </Card.Body>
    </Card>
  );
};

export default FinancingProjectionCard;
