import { RoundTexts } from "../../api-client";

export function getBidRangeLabels(texts: RoundTexts): string[] {
  return [texts.bid.greenLabel, texts.bid.redLabel];
}

export function getAmountLevelLabels(
  texts: RoundTexts,
  requiredAmountLevels: number,
): string[] {
  if (requiredAmountLevels === 1) {
    return [texts.bid.amountLabel];
  }
  return [
    texts.bid.level1Label,
    texts.bid.level2Label,
    texts.bid.level3Label,
  ].slice(0, requiredAmountLevels);
}
