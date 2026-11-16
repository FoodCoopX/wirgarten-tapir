import { formatCurrency } from "./formatCurrency.ts";

export function formatEuro(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "–";
  }
  return formatCurrency(Number(value));
}

export function formatNumber(
  value: number | string | null | undefined,
): string {
  if (value === null || value === undefined || value === "") {
    return "–";
  }
  return Number(value).toLocaleString("de-DE", {
    maximumFractionDigits: 2,
  });
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "–";
  }
  return `${value.toFixed(1)} %`;
}

// Interpolate between the green/yellow/red anchors along the 0/50/100 axis.
export function interpolateLevel(
  green: number,
  yellow: number,
  red: number,
  position: number,
): number {
  if (position <= 50) {
    return green + (yellow - green) * (position / 50);
  }
  return yellow + (red - yellow) * ((position - 50) / 50);
}

export function coverageVariant(coverage: number): string {
  if (coverage >= 100) {
    return "success";
  }
  if (coverage >= 90) {
    return "warning";
  }
  return "danger";
}

// Discrete bid level for a position on the 0/50/100 axis (0 -> 1, 50 -> 2, ...).
export function levelFromPosition(position: number, bidLevels: number): number {
  const level = Math.round(position / 50) + 1;
  return Math.min(Math.max(level, 1), Math.max(bidLevels, 1));
}
