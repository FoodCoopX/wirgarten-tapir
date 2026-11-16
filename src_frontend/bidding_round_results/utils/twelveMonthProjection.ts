import type { ChartData } from "chart.js";

import { interpolate } from "../../utils/interpolate.ts";
import { levelFromPosition } from "../../utils/resultsFormat.ts";
import type { TwelveMonthProjection, TwelveMonthSeries } from "../types.ts";
import type {
  FinancingProjectionData,
  FinancingProjectionResult,
  MemberWithBid,
} from "./financingProjection.ts";
import { computeFinancingProjection } from "./financingProjection.ts";

interface TwelveMonthProjectionInput {
  financingProjection: FinancingProjectionData;
  dynamicProjection: FinancingProjectionResult;
  includeAutoRenewed: boolean;
  surchargeOnBids: boolean;
  surchargeOnAverage: boolean;
  surchargeFactor: number;
  members: MemberWithBid[];
  isBidRange: boolean;
  bidLevels: number;
  bidRangePosition: number;
  newMembersPerMonth: number;
  bidReachedByPosition: number[];
}

const MONTHS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

// 12-month projection: the admin estimates how many new members join per month
// (slider). The chart combines the member growth (bars, cumulative) with the
// cumulative balance (lines) for each bid level and the current dynamic level.
export function computeTwelveMonthProjection(
  input: TwelveMonthProjectionInput,
): TwelveMonthProjection {
  const {
    financingProjection,
    dynamicProjection,
    includeAutoRenewed,
    surchargeOnBids,
    surchargeOnAverage,
    surchargeFactor,
    members,
    isBidRange,
    bidLevels,
    bidRangePosition,
    newMembersPerMonth,
  } = input;
  const months = MONTHS;
  const openShares = Number(financingProjection.remainingShares ?? 0);
  const monthlyTarget = dynamicProjection.target / 12;

  const joinedBy = (month: number) =>
    Math.min(newMembersPerMonth * month, openShares);
  const membersData = months.map((month) => joinedBy(month));

  const saldoFor = (projectionAtLevel: FinancingProjectionResult) => {
    const committedMonthly =
      (projectionAtLevel.bidReached +
        projectionAtLevel.autoTotal +
        projectionAtLevel.otherFixed) /
      12;
    const perShareMonthly = projectionAtLevel.averagePerSharePerMonth;
    let revenueCumulative = 0;
    let costsCumulative = 0;
    return months.map((month) => {
      if (month === 0) {
        return 0;
      }
      revenueCumulative += committedMonthly + joinedBy(month) * perShareMonthly;
      costsCumulative += monthlyTarget;
      return revenueCumulative - costsCumulative;
    });
  };

  const projectionAt = (position: number) =>
    computeFinancingProjection(
      financingProjection,
      position,
      includeAutoRenewed,
      {
        surchargeOnBids,
        surchargeOnAverage,
        surchargeFactor,
        members,
        isBidRange,
        bidReached: surchargeOnBids
          ? input.bidReachedByPosition[Math.round(position)]
          : undefined,
      },
    );

  const currentLabel = isBidRange
    ? interpolate("Saldo dynamisch (Niveau {position})", {
        position: bidRangePosition,
      })
    : interpolate("Saldo Stufe {level}", {
        level: levelFromPosition(bidRangePosition, bidLevels),
      });
  const series: TwelveMonthSeries[] = [];
  if (isBidRange) {
    series.push(
      {
        label: "Saldo Grün (Wunsch)",
        color: "#198754",
        data: saldoFor(projectionAt(0)),
      },
      {
        label: "Saldo Rot (Schmerzgrenze)",
        color: "#dc3545",
        data: saldoFor(projectionAt(100)),
      },
    );
  } else {
    const palette = ["#198754", "#ffc107", "#dc3545"];
    for (let level = 1; level <= bidLevels; level++) {
      series.push({
        label: interpolate("Saldo Gebot {level}", { level }),
        color: palette[level - 1] ?? "#0d6efd",
        data: saldoFor(projectionAt((level - 1) * 50)),
      });
    }
  }
  series.push({
    label: currentLabel,
    color: "#fd7e14",
    data: saldoFor(dynamicProjection),
  });

  const currentSaldo = saldoFor(dynamicProjection);
  let breakEvenMonth: number | null = null;
  for (let month = 1; month <= 12; month++) {
    if (currentSaldo[month] >= -0.01) {
      breakEvenMonth = month;
      break;
    }
  }

  return {
    openShares,
    breakEvenMonth,
    saldoAfterTwelveMonths: currentSaldo[12],
    chartData: {
      labels: months.map((month) =>
        month === 0 ? "Start" : interpolate("Monat {month}", { month }),
      ),
      datasets: [
        {
          type: "bar",
          label: "Neue Mitglieder (kumuliert)",
          data: membersData,
          backgroundColor: "rgba(13,110,253,0.55)",
          yAxisID: "members",
        },
        ...series.map((entry) => ({
          type: "line" as const,
          label: entry.label,
          data: entry.data,
          borderColor: entry.color,
          backgroundColor: entry.color,
          borderWidth: entry.label === currentLabel ? 3 : 1.5,
          borderDash: entry.label === currentLabel ? undefined : [5, 3],
          tension: 0.2,
          pointRadius: 0,
          yAxisID: "saldo",
        })),
        {
          type: "line",
          label: "Break-even (0 €)",
          data: months.map(() => 0),
          borderColor: "#adb5bd",
          borderDash: [6, 4],
          pointRadius: 0,
          yAxisID: "saldo",
        },
      ],
    } as unknown as ChartData<"bar">,
  };
}
