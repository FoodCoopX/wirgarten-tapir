import { RoundTexts } from "../../api-client";

export function getLevelLabels(
  isBidRange: boolean,
  requiredAmountLevels: number,
  texts: RoundTexts,
): string[] {
  if (isBidRange) {
    return [texts.bid.greenLabel, texts.bid.redLabel];
  }
  if (requiredAmountLevels === 1) {
    return [texts.bid.amountLabel];
  }
  return Array.from(
    { length: requiredAmountLevels },
    (_, index) => `Stufe ${index + 1}`,
  );
}
