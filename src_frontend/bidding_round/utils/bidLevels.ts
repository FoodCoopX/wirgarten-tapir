import {
  BiddingRoundRound,
  BiddingRoundTexts,
} from "../types/BiddingRoundTypes.ts";

export type BiddingRoundAmountKey = "amount1" | "amount2" | "amount3";

export function getBidLevels(round?: BiddingRoundRound): number {
  const trafficLight = round?.biddingProcedure === "traffic_light";
  return trafficLight ? 3 : Math.min(Math.max(round?.bidLevels ?? 1, 1), 3);
}

export function getBidAmountKey(level: number): BiddingRoundAmountKey {
  return `amount${level}` as BiddingRoundAmountKey;
}

export function getBidLevelLabel(
  level: number,
  bidLevels: number,
  texts: BiddingRoundTexts,
): string {
  if (bidLevels === 1) {
    return texts.bid.amountLabel;
  }
  if (level === 1) {
    return texts.bid.level1Label;
  }
  if (level === 2) {
    return texts.bid.level2Label;
  }
  return texts.bid.level3Label;
}

/**
 * Parses a user-entered euro amount. Accepts "," or "." as decimal separator,
 * optional whitespace and a trailing "€", at most two decimal places. Returns
 * null for empty or invalid input.
 */
export function parseEuroAmount(
  raw: string | number | null | undefined,
): number | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  const normalized = raw.toString().replace(/[\s€]/g, "").replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return null;
  }
  return Number.parseFloat(normalized);
}

/**
 * Filters a raw input string so that only a valid (partial) euro amount can be
 * typed: digits with an optional "," or "." and at most two decimals.
 */
export function sanitizeEuroAmountInput(raw: string): string {
  const cleaned = raw.replace(/[\s€]/g, "").replace(",", ".");
  const match = cleaned.match(/^\d*(?:\.\d{0,2})?/);
  return match ? match[0] : "";
}

/** Normalises a euro amount string to a dot decimal for the API. */
export function toDotDecimal(raw: string | null | undefined): string | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  const normalized = raw.toString().replace(/[\s€]/g, "").replace(",", ".");
  return normalized === "" ? null : normalized;
}

/** Formats a number as a euro amount with two decimals and a dot separator. */
export function formatEuroNumber(value: number): string {
  return (Math.round(value * 100) / 100).toFixed(2);
}

/**
 * Builds the default bid amounts for a variant: reference value, +5 % and
 * +10 % for the first three levels (single-level bids get only the reference
 * value). Returns one entry per level, formatted as euro strings.
 */
export function buildStandardAmounts(
  referenceValue: string | null | undefined,
  bidLevels: number,
): string[] {
  const count = Math.max(bidLevels, 1);
  const reference = parseEuroAmount(referenceValue);
  if (reference === null) {
    return Array.from({ length: count }, () => "");
  }
  const factors = [1, 1.05, 1.1];
  return Array.from({ length: count }, (_, index) =>
    formatEuroNumber(reference * (factors[index] ?? 1.1)),
  );
}
