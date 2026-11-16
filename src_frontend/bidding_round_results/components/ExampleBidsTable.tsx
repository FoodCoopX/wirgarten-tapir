import React from "react";
import { Button, Collapse, Table } from "react-bootstrap";

import { interpolate } from "../../utils/interpolate.ts";
import { formatEuro } from "../../utils/resultsFormat.ts";
import { effectiveAmount, EXAMPLE_BIDS } from "../utils/financingProjection.ts";

interface ExampleBidsTableProps {
  isBidRange: boolean;
  bidRangePosition: number;
  surchargeOnBids: boolean;
  surchargePercent: number;
  surchargeFactor: number;
  showExample: boolean;
  onToggle: () => void;
}

const ExampleBidsTable: React.FC<ExampleBidsTableProps> = ({
  isBidRange,
  bidRangePosition,
  surchargeOnBids,
  surchargePercent,
  surchargeFactor,
  showExample,
  onToggle,
}) => {
  if (!isBidRange) {
    return null;
  }

  return (
    <div className="mt-3">
      <Button variant="link" className="p-0" onClick={onToggle}>
        {showExample ? "Beispiel ausblenden" : "Beispiel anzeigen"}
      </Button>
      <Collapse in={showExample} mountOnEnter unmountOnExit>
        <div>
          <p className="text-muted small mt-2 mb-1">
            {interpolate(
              "Beispielgebote und ihr effektiver Betrag bei der aktuellen Regler-Position ({position}):",
              { position: bidRangePosition },
            )}
          </p>
          <Table size="sm" className="mb-0">
            <thead>
              <tr>
                <th>{"Gebot"}</th>
                <th className="text-end">{"Grün (Wunsch)"}</th>
                <th className="text-end">{"Rot (Schmerzgrenze)"}</th>
                <th className="text-end">
                  {interpolate("Effektiv (Position {position})", {
                    position: bidRangePosition,
                  })}
                  {surchargeOnBids && surchargePercent > 0
                    ? interpolate(", inkl. Aufschlag +{percent} %", {
                        percent: surchargePercent,
                      })
                    : ""}
                </th>
              </tr>
            </thead>
            <tbody>
              {EXAMPLE_BIDS.map((bid) => (
                <tr key={bid.label}>
                  <td>{bid.label}</td>
                  <td className="text-end">{formatEuro(bid.green)}</td>
                  <td className="text-end">{formatEuro(bid.red)}</td>
                  <td className="text-end fw-bold">
                    {formatEuro(
                      effectiveAmount(
                        bid.green,
                        bid.yellow,
                        bid.red,
                        bidRangePosition,
                        surchargeOnBids,
                        surchargeFactor,
                        isBidRange,
                      ),
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </Collapse>
    </div>
  );
};

export default ExampleBidsTable;
