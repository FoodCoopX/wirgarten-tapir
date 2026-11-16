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
