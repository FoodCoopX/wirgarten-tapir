import React from "react";
import { Collapse } from "react-bootstrap";

import { interpolate } from "../../utils/interpolate.ts";

interface FinancingFormulaDetailsProps {
  show: boolean;
  isBidRange: boolean;
  bidLevels: number;
  membershipIncludedInProductType: boolean;
  membershipFeesApply: boolean;
}

const FinancingFormulaDetails: React.FC<FinancingFormulaDetailsProps> = ({
  show,
  isBidRange,
  bidLevels,
  membershipIncludedInProductType,
  membershipFeesApply,
}) => {
  return (
    <Collapse in={show} mountOnEnter unmountOnExit>
      <div className="text-muted small mt-1">
        {isBidRange ? (
          <p className="mb-1">
            <strong>
              {"Der Regler interpoliert die beiden Beträge deines Gebots."}
            </strong>{" "}
            {
              "Interpolieren heißt: Der Betrag wird gleichmäßig zwischen den beiden Werten umgerechnet. Ganz links (Position 0) zählt der Wunsch (Grün), ganz rechts (100) die Schmerzgrenze (Rot)."
            }
          </p>
        ) : bidLevels > 1 ? (
          <p className="mb-1">
            <strong>{"Der Regler wählt die Gebotsstufe."}</strong>{" "}
            {interpolate(
              "Gebot 1 ist der Wunschbetrag; reicht er nicht, gilt automatisch die nächste Stufe (Gebot 1 bis Gebot {count}). Gerechnet wird mit dem Betrag der gewählten Stufe.",
              { count: bidLevels },
            )}
          </p>
        ) : (
          <p className="mb-1">
            <strong>{"Alle Gebote haben genau einen Betrag."}</strong>{" "}
            {"Gerechnet wird mit diesem Betrag."}
          </p>
        )}
        <p className="mb-1">
          <strong>{"Bietende Ø"}</strong>{" "}
          {
            "= Summe aller Gebote der Saison ÷ gebotene Ernteanteile ÷ 12 (Monate). Das ist der durchschnittliche Beitrag pro Anteil und Monat."
          }
        </p>
        <p className="mb-1">
          <strong>{"Nicht-Bietende Ø"}</strong>{" "}
          {
            "= (Ziel − Gebote der Bietenden − Mitgliedsbeiträge − Lieferzuschlag) ÷ (Auto-Verlängerer-Anteile + offene Anteile) ÷ 12. Er ist so gewählt, dass das Ziel bei voller Auslastung gedeckt ist."
          }{" "}
          {"Nicht-Bietende zahlen dabei mindestens das Ø-Gebot der Bietenden."}
          {membershipIncludedInProductType && (
            <>
              {" "}
              {
                "Mitgliedsbeiträge: an den Ernteanteil angerechnet, daher nicht separat gerechnet."
              }
            </>
          )}
          {!membershipIncludedInProductType && membershipFeesApply && (
            <>
              {" "}
              {
                "Mitgliedsbeiträge: werden als eigener fester Beitrag gerechnet."
              }
            </>
          )}
        </p>
        <p className="mb-1">
          <strong>{"Summe bei voller Auslastung"}</strong>{" "}
          {
            "= Gebote der Bietenden + Mitgliedsbeiträge + Lieferzuschlag + Nicht-Bietende Ø × (Auto-Verlängerer-Anteile + offene Anteile) × 12. Bei voller Auslastung deckt diese Summe das Ziel."
          }
        </p>
        <p className="mt-1 mb-0">
          {
            "Ein optionaler Aufschlag erhöht die Gebote und/oder den Ø; bei der Gebotsspanne nie über die Schmerzgrenze (Rot) hinaus."
          }
        </p>
      </div>
    </Collapse>
  );
};

export default FinancingFormulaDetails;
