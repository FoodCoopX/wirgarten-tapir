import { RoundTexts } from "../../api-client";

export function getLevelLabels(
  texts: RoundTexts,
  isBidRange: boolean,
  requiredAmountLevels: number,
): string[] {
  return isBidRange
    ? [texts.bid.greenLabel, texts.bid.redLabel]
    : requiredAmountLevels === 1
      ? [texts.bid.amountLabel]
      : [
          texts.bid.level1Label,
          texts.bid.level2Label,
          texts.bid.level3Label,
        ].slice(0, requiredAmountLevels);
}
