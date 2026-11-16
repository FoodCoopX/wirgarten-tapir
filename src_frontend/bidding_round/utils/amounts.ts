export function parseEuroAmount(raw: string | null | undefined): number | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  const normalized = raw.toString().replace(/[\s€]/g, "").replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return null;
  }
  return Number.parseFloat(normalized);
}

export function sanitizeEuroAmountInput(raw: string): string {
  const cleaned = raw.replace(/[\s€]/g, "").replace(",", ".");
  const match = cleaned.match(/^\d*(?:\.\d{0,2})?/);
  return match ? match[0] : "";
}

export function toDotDecimal(raw: string | null | undefined): string | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  const normalized = raw.toString().replace(/[\s€]/g, "").replace(",", ".");
  return normalized === "" ? null : normalized;
}

export { formatAmountNumber } from "../../utils/formatAmountNumber.ts";

export function getMonthlyTotal(amount: number, quantity: number): number {
  return amount * quantity;
}

export function getYearlyAmount(amount: number, quantity: number): number {
  return getMonthlyTotal(amount, quantity) * 12;
}


export interface BidLevelCost {
  amount: number | null;
  bidMonthly: number | null;
  bidYearly: number | null;
  membershipMonthly: number | null;
  deliveryMonthly: number | null;
  deliveryYearly: number | null;
  totalMonthly: number | null;
  totalYearly: number | null;
}

export function getBidLevelCost(
  amount: number | null,
  quantity: number,
  membershipPrice: number | null,
  deliveryYearly: number | null,
): BidLevelCost {
  const membershipMonthly =
    membershipPrice !== null && membershipPrice > 0 ? membershipPrice : null;
  const delivery =
    deliveryYearly !== null && deliveryYearly > 0 ? deliveryYearly : null;
  const deliveryMonthly = delivery === null ? null : delivery / 12;
  const bidMonthly = amount === null ? null : getMonthlyTotal(amount, quantity);
  const bidYearly = amount === null ? null : getYearlyAmount(amount, quantity);

  return {
    amount,
    bidMonthly,
    bidYearly,
    membershipMonthly,
    deliveryMonthly,
    deliveryYearly: delivery,
    totalMonthly:
      bidMonthly === null
        ? null
        : bidMonthly + (membershipMonthly ?? 0) + (deliveryMonthly ?? 0),
    totalYearly:
      bidYearly === null
        ? null
        : bidYearly + (membershipMonthly ?? 0) * 12 + (delivery ?? 0),
  };
}

export function getBidTotalRange(
  amounts: string[],
  requiredAmountLevels: number,
  quantity: number,
  membershipPrice: number | null,
  deliveryYearly: number | null,
): { min: number; max: number } | null {
  const totals: number[] = [];

  for (let index = 0; index < requiredAmountLevels; index += 1) {
    const cost = getBidLevelCost(
      parseEuroAmount(amounts[index]),
      quantity,
      membershipPrice,
      deliveryYearly,
    );
    if (cost.bidMonthly !== null) {
      totals.push(cost.bidMonthly + (cost.membershipMonthly ?? 0));
    }
  }

  if (totals.length === 0) {
    return null;
  }

  return { min: Math.min(...totals), max: Math.max(...totals) };
}

export function scaleAmountsForVariant(
  amounts: string[],
  previousReference: number,
  nextReference: number,
): string[] {
  if (
    previousReference <= 0 ||
    nextReference <= 0 ||
    previousReference === nextReference
  ) {
    return amounts;
  }
  const factor = nextReference / previousReference;
  return amounts.map((value) => {
    const amount = parseEuroAmount(value);
    return amount === null ? value : (amount * factor).toFixed(2);
  });
}
