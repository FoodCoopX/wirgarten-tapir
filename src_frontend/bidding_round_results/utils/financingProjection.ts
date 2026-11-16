import { interpolateLevel } from "../../utils/resultsFormat.ts";

export interface BidAmounts {
  amount1?: string | number | null;
  amount2?: string | number | null;
  amount3?: string | number | null;
  quantity: number;
}

export interface MemberWithBid {
  amount1?: string | number | null;
  amount2?: string | number | null;
  amount3?: string | number | null;
  quantity?: number;
  bid?: BidAmounts | null;
}

export interface ProjectionLevel {
  reachedPerYear: string | number;
  averagePerSharePerMonth?: string | number;
}

export interface FinancingProjectionData {
  levels: {
    green: ProjectionLevel;
    yellow?: ProjectionLevel;
    red: ProjectionLevel;
  };
  bidShares: string | number;
  targetPerYear: string | number;
  membershipPerYear?: string | number;
  deliveryChargePerYear?: string | number;
  autoShares?: string | number;
  remainingShares?: string | number;
  capacityShares: string | number;
}

export interface ProjectionOptions {
  surchargeOnBids?: boolean;
  surchargeOnAverage?: boolean;
  surchargeFactor?: number;
  members?: MemberWithBid[];
  isBidRange?: boolean;
  bidReached?: number;
  bidReachedByPosition?: number[];
}

export interface FinancingProjectionResult {
  baseBidReached: number;
  bidReached: number;
  bidderAveragePerMonth: number;
  baseAverage: number;
  averagePerSharePerMonth: number;
  otherFixed: number;
  autoTotal: number;
  latecomerTotal: number;
  baseAutoTotal: number;
  baseLatecomerTotal: number;
  baseTotal: number;
  surchargeTotal: number;
  payerShares: number;
  total: number;
  currentTotal: number;
  currentCoverage: number;
  target: number;
  coverage: number;
  currentShares: number;
  capacityShares: number;
  utilization: number;
}

export interface ExampleBid {
  label: string;
  green: number;
  yellow: number;
  red: number;
}

function interpolateTwoLevels(
  green: number,
  red: number,
  position: number,
): number {
  return green + (red - green) * (position / 100);
}

export function itemLevels(item: BidAmounts, isBidRange = false) {
  const a1 = item.amount1 != null ? Number(item.amount1) : null;
  const a2 = item.amount2 != null ? Number(item.amount2) : null;
  const a3 = item.amount3 != null ? Number(item.amount3) : null;
  if (isBidRange) {
    const green = a1 ?? a2 ?? 0;
    const red = a2 ?? a1 ?? 0;
    return { a1, a2, a3, base: green, green, yellow: red, red };
  }
  const base = a2 ?? a1 ?? a3 ?? 0;
  return {
    a1,
    a2,
    a3,
    base,
    green: a1 ?? base,
    yellow: a2 ?? base,
    red: a3 ?? base,
  };
}

// Amount of a bid item at a position on the 0/100 axis. The bid range
// interpolates between green and red; simple rounds keep the 0/50/100 levels.
export function itemAmountAtPosition(
  item: BidAmounts,
  position: number,
  isBidRange = false,
): number {
  const levels = itemLevels(item, isBidRange);
  return isBidRange
    ? interpolateTwoLevels(levels.green, levels.red, position)
    : interpolateLevel(levels.green, levels.yellow, levels.red, position);
}

// Effective amount at the chosen level. For the bid range the optional surcharge
// is capped at the pain threshold (red); the simple procedure has no cap.
export function effectiveAmount(
  green: number,
  yellow: number,
  red: number,
  position: number,
  applySurcharge: boolean,
  factor: number,
  isBidRange: boolean,
): number {
  const base = isBidRange
    ? interpolateTwoLevels(green, red, position)
    : interpolateLevel(green, yellow, red, position);
  if (!applySurcharge) {
    return base;
  }
  return isBidRange ? Math.min(base * factor, red) : base * factor;
}

// Illustrative example bids (green / yellow / red) used in the expandable example.
export const EXAMPLE_BIDS: ExampleBid[] = [
  { label: "Gebot A", green: 60, yellow: 80, red: 100 },
  { label: "Gebot B", green: 70, yellow: 85, red: 105 },
  { label: "Gebot C", green: 50, yellow: 75, red: 95 },
];

// Apply the surcharge to the bids, never exceeding each bid's pain threshold (red).
export function computeUpliftedBidReached(
  members: MemberWithBid[],
  position: number,
  factor: number,
  applyToBids: boolean,
  isBidRange: boolean,
): number {
  let total = 0;
  for (const entry of members) {
    const item = entry.bid ?? entry;
    if (item.quantity == null) continue;
    const levels = itemLevels(item as BidAmounts, isBidRange);
    const value = effectiveAmount(
      levels.green,
      levels.yellow,
      levels.red,
      position,
      applyToBids,
      factor,
      isBidRange,
    );
    total += value * item.quantity * 12;
  }
  return total;
}

export function buildUpliftedReachedByPosition(
  members: MemberWithBid[],
  factor: number,
  applyToBids: boolean,
  isBidRange: boolean,
): number[] {
  return Array.from({ length: 101 }, (_, position) =>
    computeUpliftedBidReached(
      members,
      position,
      factor,
      applyToBids,
      isBidRange,
    ),
  );
}

/**
 * Fair model: bidders pay their bid at the chosen solidarity level; everyone who
 * did not bid (auto-renewed members and members joining after the round) pays the
 * same dynamic average bid, derived so the target is covered at full capacity.
 * An optional surcharge can be applied to the bids and/or to the average to also
 * cover the gap of unallocated shares. For the bid range the surcharge is capped
 * at the pain threshold (red); the simple procedure has no cap.
 *
 * This is a what-if projection for the solidarity slider. Contract prices use
 * `max(reference_value, locked bidder average)`; see docs/dev/bidding_round.md.
 */
export function computeFinancingProjection(
  projection: FinancingProjectionData,
  position: number,
  includeAutoRenewed: boolean,
  options: ProjectionOptions = {},
): FinancingProjectionResult {
  const isBidRange = options.isBidRange ?? false;
  const levels = projection.levels;
  const greenReached = Number(levels.green.reachedPerYear);
  const redReached = Number(levels.red.reachedPerYear);
  const baseBidReached = isBidRange
    ? interpolateTwoLevels(greenReached, redReached, position)
    : interpolateLevel(
        greenReached,
        Number(levels.yellow?.reachedPerYear ?? greenReached),
        redReached,
        position,
      );

  const factor = options.surchargeFactor ?? 1;
  const bidReached =
    options.bidReached !== undefined
      ? options.bidReached
      : options.surchargeOnBids && options.members
        ? computeUpliftedBidReached(
            options.members,
            position,
            factor,
            true,
            isBidRange,
          )
        : baseBidReached;

  const bidShares = Number(projection.bidShares);
  const bidderAveragePerMonth =
    bidShares > 0 ? bidReached / (bidShares * 12) : 0;

  const target = Number(projection.targetPerYear);
  const otherFixed =
    Number(projection.membershipPerYear ?? 0) +
    Number(projection.deliveryChargePerYear ?? 0);
  const autoShares = Number(projection.autoShares ?? 0);
  const remainingShares = Number(projection.remainingShares ?? 0);
  const payerShares = includeAutoRenewed
    ? autoShares + remainingShares
    : remainingShares;

  // Base average derived so the target is covered at full capacity (no surcharge).
  // With the non-bidder floor, non-bidders pay at least the bidders' average.
  let baseAverage =
    payerShares > 0
      ? (target - otherFixed - baseBidReached) / (payerShares * 12)
      : 0;
  baseAverage = Math.max(baseAverage, bidderAveragePerMonth);
  const redAverage = Number(levels.red.averagePerSharePerMonth ?? baseAverage);
  let averagePerSharePerMonth = options.surchargeOnAverage
    ? isBidRange
      ? Math.min(baseAverage * factor, redAverage)
      : baseAverage * factor
    : baseAverage;
  // The floor always holds, even after the surcharge cap.
  averagePerSharePerMonth = Math.max(
    averagePerSharePerMonth,
    bidderAveragePerMonth,
  );

  const autoTotal = includeAutoRenewed
    ? autoShares * averagePerSharePerMonth * 12
    : 0;
  const latecomerTotal = remainingShares * averagePerSharePerMonth * 12;
  const total = bidReached + otherFixed + autoTotal + latecomerTotal;
  const coverage = target > 0 ? (total / target) * 100 : 0;

  // Contributions from the members already in the round (without latecomers).
  const currentTotal = bidReached + otherFixed + autoTotal;
  const currentCoverage = target > 0 ? (currentTotal / target) * 100 : 0;

  // Base model (without surcharge) and the surcharge share, so it can be shown
  // as its own line in the breakdown.
  const baseAutoTotal = includeAutoRenewed ? autoShares * baseAverage * 12 : 0;
  const baseLatecomerTotal = remainingShares * baseAverage * 12;
  const baseTotal =
    baseBidReached + otherFixed + baseAutoTotal + baseLatecomerTotal;
  const surchargeTotal = total - baseTotal;

  const capacityShares = Number(projection.capacityShares);
  const currentShares = bidShares + (includeAutoRenewed ? autoShares : 0);
  const utilization =
    capacityShares > 0 ? (currentShares / capacityShares) * 100 : 0;

  return {
    baseBidReached,
    bidReached,
    bidderAveragePerMonth,
    baseAverage,
    averagePerSharePerMonth,
    otherFixed,
    autoTotal,
    latecomerTotal,
    baseAutoTotal,
    baseLatecomerTotal,
    baseTotal,
    surchargeTotal,
    payerShares,
    total,
    currentTotal,
    currentCoverage,
    target,
    coverage,
    currentShares,
    capacityShares,
    utilization,
  };
}

export function findTargetCoveragePosition(
  projection: FinancingProjectionData | null | undefined,
  includeAutoRenewed: boolean,
  options: ProjectionOptions & { bidLevels?: number },
): { position: number; targetCovered: boolean } {
  if (!projection) {
    return { position: 50, targetCovered: false };
  }
  if (options.isBidRange) {
    for (let position = 0; position <= 100; position += 1) {
      const current = computeFinancingProjection(
        projection,
        position,
        includeAutoRenewed,
        {
          ...options,
          bidReached: options.bidReachedByPosition?.[position],
        },
      );
      if (current.currentCoverage >= 100) {
        return { position, targetCovered: true };
      }
    }
    return { position: 100, targetCovered: false };
  }
  const bidLevels = Math.max(1, options.bidLevels ?? 1);
  for (let level = 1; level <= bidLevels; level += 1) {
    const position = (level - 1) * 50;
    const current = computeFinancingProjection(
      projection,
      position,
      includeAutoRenewed,
      {
        ...options,
        bidReached: options.bidReachedByPosition?.[position],
      },
    );
    if (current.currentCoverage >= 100) {
      return { position, targetCovered: true };
    }
  }
  return { position: (bidLevels - 1) * 50, targetCovered: false };
}
