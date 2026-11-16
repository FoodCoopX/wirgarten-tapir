import type { Bid } from "../../api-client/models/Bid.ts";
import { effectiveAmount, itemLevels } from "./financingProjection.ts";

interface ItemDescription {
  productTypeName: string;
  productName: string;
  quantity: number;
}

function describeItems(items: ItemDescription[]): string {
  return items
    .map(
      (item) =>
        `${item.productTypeName} (${item.productName}) ×${item.quantity}`,
    )
    .join(", ");
}

export function renderMemberItems(bid: Bid | null | undefined): string {
  if (!bid) return "–";
  return `${bid.productName} ×${bid.quantity}`;
}

export function renderContractItems(
  items: ItemDescription[] | null | undefined,
): string {
  if (!items || items.length === 0) return "–";
  return describeItems(items);
}

export function bidAmountForLevel(
  bid: Bid | null | undefined,
  level: 1 | 2 | 3,
  isBidRange = false,
): number | null {
  if (!bid) return null;
  const levels = itemLevels(bid, isBidRange);
  const amount =
    level === 1
      ? levels.green
      : isBidRange
        ? levels.red
        : level === 2
          ? levels.yellow
          : levels.red;
  return amount * bid.quantity;
}

export function bidAmountAtPosition(
  bid: Bid | null | undefined,
  position: number,
  applySurcharge: boolean,
  factor: number,
  isBidRange: boolean,
): number | null {
  if (!bid) return null;
  const levels = itemLevels(bid, isBidRange);
  return (
    effectiveAmount(
      levels.green,
      levels.yellow,
      levels.red,
      position,
      applySurcharge,
      factor,
      isBidRange,
    ) * bid.quantity
  );
}
