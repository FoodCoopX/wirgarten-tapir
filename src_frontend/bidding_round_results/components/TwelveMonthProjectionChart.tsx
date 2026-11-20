import React from "react";
import { Badge, Button, Collapse, Form } from "react-bootstrap";
import { Bar } from "react-chartjs-2";

import { interpolate } from "../../utils/interpolate.ts";
import { formatEuro } from "../../utils/resultsFormat.ts";
import type { TwelveMonthProjection } from "../types.ts";
import "../utils/chartSetup.ts";

interface TwelveMonthProjectionChartProps {
  show: boolean;
  onToggle: () => void;
  projection: TwelveMonthProjection | null;
  newMembersPerMonth: number;
  onNewMembersPerMonthChange: (membersPerMonth: number) => void;
}

const TwelveMonthProjectionChart: React.FC<TwelveMonthProjectionChartProps> = ({
  show,
  onToggle,
  projection,
  newMembersPerMonth,
  onNewMembersPerMonthChange,
}) => {
  return (
    <div className="mt-3">
      <Button variant="link" className="p-0" onClick={onToggle}>
        {show ? "12-Monats-Prognose ausblenden" : "12-Monats-Prognose anzeigen"}
      </Button>
      <Collapse in={show} mountOnEnter unmountOnExit>
        <div className="mt-2 p-3 bg-light rounded">
          <h6 className="mb-1">{"12-Monats-Prognose"}</h6>
          <p className="text-muted small mb-2">
            {
              "Geschätzte Anzahl neuer Mitglieder (je 1 Anteil) pro Monat. Der Graph zeigt den kumulierten Saldo (Beiträge − anteilige Kosten) über 12 Monate: unter der 0-Linie = Verlust, Erreichen der 0-Linie = Break-even."
            }
          </p>
          <Form.Group className="mb-2">
            <Form.Label className="small mb-0">
              {"Neue Mitglieder je Monat:"}{" "}
              <strong>{newMembersPerMonth}</strong>
            </Form.Label>
            <Form.Range
              min={1}
              max={Math.max(1, Math.ceil(projection?.openShares ?? 1))}
              step={1}
              value={newMembersPerMonth}
              onChange={(event) =>
                onNewMembersPerMonthChange(Number(event.target.value))
              }
              aria-label={"Neue Mitglieder je Monat"}
            />
          </Form.Group>
          <div className="mb-2">
            {projection?.breakEvenMonth != null ? (
              <Badge bg="success">
                {interpolate(
                  "Break-even ab Monat {month} — positiver Saldo nach 12 Monaten: +{amount}",
                  {
                    month: projection.breakEvenMonth,
                    amount: formatEuro(projection.saldoAfterTwelveMonths),
                  },
                )}
              </Badge>
            ) : (
              <Badge bg="danger">
                {interpolate(
                  "Kein Break-even in 12 Monaten — Saldo: {amount}",
                  {
                    amount: formatEuro(projection?.saldoAfterTwelveMonths ?? 0),
                  },
                )}
              </Badge>
            )}
          </div>
          <Bar
            data={projection?.chartData ?? { labels: [], datasets: [] }}
            options={{
              responsive: true,
              scales: {
                members: {
                  position: "left",
                  suggestedMin: 0,
                  title: {
                    display: true,
                    text: "Neue Mitglieder (kumuliert)",
                  },
                },
                saldo: {
                  position: "right",
                  grid: { drawOnChartArea: false },
                  title: {
                    display: true,
                    text: "Saldo (€)",
                  },
                },
              },
            }}
          />
        </div>
      </Collapse>
    </div>
  );
};

export default TwelveMonthProjectionChart;
