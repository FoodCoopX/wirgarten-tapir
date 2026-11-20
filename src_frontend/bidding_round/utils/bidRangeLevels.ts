export type BiddingRoundAmountKey = "amount1" | "amount2";

export type BidRangeLevel = {
  key: BiddingRoundAmountKey;
  color: "success" | "danger";
  textClass: string;
  bgClass: string;
  borderClass: string;
  dotClass: string;
};

export const BID_RANGE_LEVELS: BidRangeLevel[] = [
  {
    key: "amount1",
    color: "success",
    textClass: "text-success",
    bgClass: "bg-success-subtle",
    borderClass: "border-success",
    dotClass: "bg-success",
  },
  {
    key: "amount2",
    color: "danger",
    textClass: "text-danger",
    bgClass: "bg-danger-subtle",
    borderClass: "border-danger",
    dotClass: "bg-danger",
  },
];

const DEFAULT_LABELS: Record<BiddingRoundAmountKey, string> = {
  amount1: "Grün (Wunsch)",
  amount2: "Rot (Schmerzgrenze)",
};

export function getBidRangeDefaultLabel(level: BidRangeLevel): string {
  return DEFAULT_LABELS[level.key];
}
