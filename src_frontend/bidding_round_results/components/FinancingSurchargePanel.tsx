import React from "react";
import { Badge, Collapse, Form, ProgressBar } from "react-bootstrap";

import { coverageVariant, formatPercent } from "../../utils/resultsFormat.ts";

interface FinancingSurchargePanelProps {
  show: boolean;
  isBidRange: boolean;
  surchargePercent: number;
  onSurchargePercentChange: (percent: number) => void;
  surchargeOnBids: boolean;
  onSurchargeOnBidsChange: (enabled: boolean) => void;
  surchargeOnAverage: boolean;
  onSurchargeOnAverageChange: (enabled: boolean) => void;
  averageBidLocked: boolean;
  currentCoverage: number;
}

const FinancingSurchargePanel: React.FC<FinancingSurchargePanelProps> = ({
  show,
  isBidRange,
  surchargePercent,
  onSurchargePercentChange,
  surchargeOnBids,
  onSurchargeOnBidsChange,
  surchargeOnAverage,
  onSurchargeOnAverageChange,
  averageBidLocked,
  currentCoverage,
}) => {
  return (
    <Collapse in={show} mountOnEnter unmountOnExit>
      <div className="mt-2 p-3 bg-light rounded">
        <h6 className="mb-1">{"Aufschlag (Ausgleich offener Anteile)"}</h6>
        <p className="text-muted small mb-2">
          {
            "Hebe die Beiträge an, damit das Ziel auch ohne die offenen Anteile gedeckt ist."
          }
          {isBidRange ? (
            <>
              {" "}
              {"Der Aufschlag geht"}{" "}
              <strong>{"nie über die Schmerzgrenze (Rot)"}</strong>.
            </>
          ) : null}
        </p>
        <Form.Group className="mb-2">
          <Form.Label className="small mb-0">
            {"Aufschlag:"} <strong>{surchargePercent} %</strong>
          </Form.Label>
          <Form.Range
            min={0}
            max={100}
            step={1}
            value={surchargePercent}
            onChange={(event) =>
              onSurchargePercentChange(Number(event.target.value))
            }
            disabled={averageBidLocked}
            aria-label={"Aufschlag"}
          />
        </Form.Group>
        <div className="d-flex gap-3 flex-wrap">
          <Form.Check
            type="switch"
            label={"Auf Gebote"}
            checked={surchargeOnBids}
            onChange={(event) => onSurchargeOnBidsChange(event.target.checked)}
            disabled={averageBidLocked}
          />
          <Form.Check
            type="switch"
            label={"Auf Durchschnittsgebot"}
            checked={surchargeOnAverage}
            onChange={(event) =>
              onSurchargeOnAverageChange(event.target.checked)
            }
            disabled={averageBidLocked}
          />
        </div>
        <div className="d-flex justify-content-between align-items-center mt-2">
          <span>{"Deckung durch aktuelle Mitglieder (ohne Nachzügler)"}</span>
          <Badge bg={coverageVariant(currentCoverage)}>
            {formatPercent(currentCoverage)}
          </Badge>
        </div>
        <ProgressBar
          className="mt-1"
          variant={coverageVariant(currentCoverage)}
          now={Math.min(currentCoverage, 100)}
          label={formatPercent(currentCoverage)}
        />
      </div>
    </Collapse>
  );
};

export default FinancingSurchargePanel;
