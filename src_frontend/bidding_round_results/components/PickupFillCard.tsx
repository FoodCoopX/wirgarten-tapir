import type { ChartData } from "chart.js";
import React, { useMemo } from "react";
import { ProgressBar, Table } from "react-bootstrap";
import { Bar } from "react-chartjs-2";

import { formatNumber, formatPercent } from "../../utils/resultsFormat.ts";
import type { BiddingRoundPickupFillRow } from "../types.ts";
import "../utils/chartSetup.ts";
import CollapsibleCard from "./CollapsibleCard.tsx";

interface PickupFillCardProps {
  open: boolean;
  onToggle: () => void;
  pickupFill: BiddingRoundPickupFillRow[];
}

const PickupFillCard: React.FC<PickupFillCardProps> = ({
  open,
  onToggle,
  pickupFill,
}) => {
  const pickupChartData: ChartData<"bar"> = useMemo(
    () => ({
      labels: pickupFill.map((entry) => entry.pickupLocationName),
      datasets: [
        {
          label: "Kapazität",
          data: pickupFill.map((entry) => Number(entry.capacity)),
          backgroundColor: "rgba(13, 110, 253, 0.6)",
        },
        {
          label: "Nachfrage",
          data: pickupFill.map((entry) => Number(entry.demand)),
          backgroundColor: "rgba(25, 135, 84, 0.6)",
        },
      ],
    }),
    [pickupFill],
  );

  return (
    <CollapsibleCard
      title={"Abholort-Füllstand"}
      open={open}
      onToggle={onToggle}
    >
      <div className="row">
        <div className="col-md-6">
          <Bar
            data={pickupChartData}
            options={{
              responsive: true,
              scales: { y: { suggestedMin: 0 } },
            }}
          />
        </div>
        <div className="col-md-6">
          <Table striped hover size="sm" responsive>
            <thead>
              <tr>
                <th>{"Verteilstation"}</th>
                <th>{"Kapazität"}</th>
                <th>{"Nachfrage"}</th>
                <th>{"Füllstand"}</th>
              </tr>
            </thead>
            <tbody>
              {pickupFill.map((entry) => (
                <tr key={entry.pickupLocationId}>
                  <td>{entry.pickupLocationName}</td>
                  <td>{formatNumber(entry.capacity)}</td>
                  <td>{formatNumber(entry.demand)}</td>
                  <td style={{ minWidth: "140px" }}>
                    <ProgressBar
                      now={Math.min(entry.fillPercent ?? 0, 100)}
                      label={formatPercent(entry.fillPercent)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </div>
    </CollapsibleCard>
  );
};

export default PickupFillCard;
