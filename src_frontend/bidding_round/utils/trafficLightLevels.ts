import { BiddingRoundBidTexts } from "../types/BiddingRoundTypes.ts";
import { BiddingRoundAmountKey } from "./bidLevels.ts";

export type TrafficLightLevel = {
  key: BiddingRoundAmountKey;
  color: "success" | "warning" | "danger";
  textClass: string;
  bgClass: string;
  borderClass: string;
  dotClass: string;
};

export const TRAFFIC_LIGHT_LEVELS: TrafficLightLevel[] = [
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
    color: "warning",
    textClass: "text-warning-emphasis",
    bgClass: "bg-warning-subtle",
    borderClass: "border-warning",
    dotClass: "bg-warning",
  },
  {
    key: "amount3",
    color: "danger",
    textClass: "text-danger",
    bgClass: "bg-danger-subtle",
    borderClass: "border-danger",
    dotClass: "bg-danger",
  },
];

export function getTrafficLightLabel(
  level: TrafficLightLevel,
  texts: BiddingRoundBidTexts,
): string {
  switch (level.key) {
    case "amount1":
      return texts.greenLabel;
    case "amount2":
      return texts.yellowLabel;
    case "amount3":
      return texts.redLabel;
  }
}

const DEFAULT_LABELS: Record<BiddingRoundAmountKey, string> = {
  amount1: "Grün (Wunsch)",
  amount2: "Gelb (Zufrieden)",
  amount3: "Rot (Schmerzgrenze)",
};

export function getTrafficLightDefaultLabel(level: TrafficLightLevel): string {
  return DEFAULT_LABELS[level.key];
}
