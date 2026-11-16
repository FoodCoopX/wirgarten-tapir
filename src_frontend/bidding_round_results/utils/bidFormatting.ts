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
  return describeItems(bid.items ?? []);
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
  return (bid.items ?? []).reduce((sum: number, item) => {
    const levels = itemLevels(item, isBidRange);
    const amount =
      level === 1
        ? levels.green
        : isBidRange
          ? levels.red
          : level === 2
            ? levels.yellow
            : levels.red;
    return sum + amount * item.quantity;
  }, 0);
}

export function bidAmountAtPosition(
  bid: Bid | null | undefined,
  position: number,
  applySurcharge: boolean,
  factor: number,
  isBidRange: boolean,
): number | null {
  if (!bid) return null;
  return (bid.items ?? []).reduce((sum: number, item) => {
    const levels = itemLevels(item, isBidRange);
    return (
      sum +
      effectiveAmount(
        levels.green,
        levels.yellow,
        levels.red,
        position,
        applySurcharge,
        factor,
        isBidRange,
      ) *
        item.quantity
    );
  }, 0);
}
