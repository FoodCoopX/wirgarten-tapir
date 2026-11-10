import React from "react";
import { Badge, ProgressBar } from "react-bootstrap";

import {
  coverageVariant,
  formatEuro,
  formatNumber,
  formatPercent,
} from "../utils/resultsFormat.ts";

interface DeckungAuslastungBarsProps {
  utilization: number;
  currentShares: number;
  capacityShares: number;
  currentCoverage: number;
  currentTotal: number;
  target: number;
}

// The utilization and current coverage bars, in a fixed order, shared by the
// admin and the public evaluation.
const DeckungAuslastungBars: React.FC<DeckungAuslastungBarsProps> = ({
  utilization,
  currentShares,
  capacityShares,
  currentCoverage,
  currentTotal,
  target,
}) => {
  return (
    <>
      <div className="d-flex justify-content-between align-items-center">
        <span>{"Aktuelle Auslastung Ernteanteile"}</span>
        <Badge bg="secondary">{formatPercent(utilization)}</Badge>
      </div>
      <ProgressBar
        className="mt-1"
        variant="info"
        now={Math.min(utilization, 100)}
        label={`${formatNumber(currentShares)} / ${formatNumber(
          capacityShares,
        )} ${"Anteile"}`}
      />

      <div className="d-flex justify-content-between align-items-center mt-2">
        <span>{"Aktuelle Deckung"}</span>
        <Badge bg={coverageVariant(currentCoverage)}>
          {formatPercent(currentCoverage)}
        </Badge>
      </div>
      <ProgressBar
        className="mt-1"
        variant={coverageVariant(currentCoverage)}
        now={Math.min(currentCoverage, 100)}
        label={`${formatEuro(currentTotal)} / ${formatEuro(target)}`}
      />
    </>
  );
};

export default DeckungAuslastungBars;
