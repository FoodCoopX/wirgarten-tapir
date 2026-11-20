import React from "react";
import { Table } from "react-bootstrap";

import type { FinancingProjection } from "../../api-client/models/FinancingProjection.ts";
import { interpolate } from "../../utils/interpolate.ts";
import {
  formatEuro,
  formatNumber,
  levelFromPosition,
} from "../../utils/resultsFormat.ts";
import type { FinancingProjectionResult } from "../utils/financingProjection.ts";

interface FinancingBreakdownTableProps {
  isBidRange: boolean;
  bidRangePosition: number;
  bidLevels: number;
  includeAutoRenewed: boolean;
  financingProjection: FinancingProjection;
  dynamicProjection: FinancingProjectionResult;
  surchargePercent: number;
  surchargeOnBids: boolean;
  surchargeOnAverage: boolean;
}

function bidderLevelLabel(
  isBidRange: boolean,
  bidRangePosition: number,
  bidLevels: number,
): string {
  if (isBidRange) {
    return interpolate("Bietende (Niveau {position})", {
      position: bidRangePosition,
    });
  }
  if (bidLevels > 1) {
    return interpolate("Bietende (Gebot {level})", {
      level: levelFromPosition(bidRangePosition, bidLevels),
    });
  }
  return "Bietende (Gebotsbetrag)";
}

function surchargeScopeLabel(onBids: boolean, onAverage: boolean): string {
  if (onBids && onAverage) {
    return " auf Gebote und Durchschnittsgebot";
  }
  if (onBids) {
    return " auf Gebote";
  }
  if (onAverage) {
    return " auf Durchschnittsgebot";
  }
  return " (inaktiv)";
}

const FinancingBreakdownTable: React.FC<FinancingBreakdownTableProps> = ({
  isBidRange,
  bidRangePosition,
  bidLevels,
  includeAutoRenewed,
  financingProjection,
  dynamicProjection,
  surchargePercent,
  surchargeOnBids,
  surchargeOnAverage,
}) => {
  return (
    <Table size="sm" className="mt-3 mb-0">
      <tbody>
        <tr>
          <td>
            {bidderLevelLabel(isBidRange, bidRangePosition, bidLevels)}
          </td>
          <td className="text-end">
            {formatEuro(dynamicProjection.baseBidReached)}
          </td>
        </tr>
        {includeAutoRenewed && (
          <tr>
            <td>
              {interpolate("Auto-Verlängerer ({count} Anteile × Ø)", {
                count: formatNumber(financingProjection.autoShares),
              })}
            </td>
            <td className="text-end">
              {formatEuro(dynamicProjection.baseAutoTotal)}
            </td>
          </tr>
        )}
        {Number(financingProjection.deliveryChargePerYear ?? 0) > 0 && (
          <tr>
            <td>{"Lieferzuschlag"}</td>
            <td className="text-end">
              {formatEuro(Number(financingProjection.deliveryChargePerYear))}
            </td>
          </tr>
        )}
        {Number(financingProjection.membershipPerYear ?? 0) > 0 && (
          <tr>
            <td>{"Mitgliedschaft"}</td>
            <td className="text-end">
              {formatEuro(Number(financingProjection.membershipPerYear))}
            </td>
          </tr>
        )}
        {surchargePercent > 0 && (
          <tr>
            <td>
              {interpolate("Aufschlag (+{percent} %)", {
                percent: surchargePercent,
              })}
              {surchargeScopeLabel(surchargeOnBids, surchargeOnAverage)}
            </td>
            <td className="text-end">
              +{formatEuro(dynamicProjection.surchargeTotal)}
            </td>
          </tr>
        )}
        <tr className="fw-bold table-light">
          <td>{"Aktuelle Deckung"}</td>
          <td className="text-end">
            {formatEuro(dynamicProjection.currentTotal)}
          </td>
        </tr>
        <tr>
          <td className="text-muted">{"Differenz zum Ziel"}</td>
          <td className="text-end text-muted">
            {formatEuro(
              dynamicProjection.target - dynamicProjection.currentTotal,
            )}
          </td>
        </tr>
        <tr>
          <td>
            {interpolate("Nachzügler ({count} Anteile × Ø)", {
              count: formatNumber(financingProjection.remainingShares),
            })}
          </td>
          <td className="text-end">
            {formatEuro(dynamicProjection.baseLatecomerTotal)}
          </td>
        </tr>
        <tr className="fw-bold">
          <td>{"Summe bei voller Auslastung"}</td>
          <td className="text-end">{formatEuro(dynamicProjection.total)}</td>
        </tr>
        <tr>
          <td>{"Ziel-Deckungsbetrag"}</td>
          <td className="text-end">{formatEuro(dynamicProjection.target)}</td>
        </tr>
        <tr>
          <td>{"Anteile geboten / Ziel"}</td>
          <td className="text-end">
            {formatNumber(
              Number(financingProjection.bidShares) +
                (includeAutoRenewed
                  ? Number(financingProjection.autoShares)
                  : 0),
            )}{" "}
            / {formatNumber(financingProjection.capacityShares)}
          </td>
        </tr>
      </tbody>
    </Table>
  );
};

export default FinancingBreakdownTable;
