import { AdminSubscriptionChangeSubscriptionUnit } from "../../api-client";

export function isSubscriptionUnitEditable(
  unit: AdminSubscriptionChangeSubscriptionUnit,
): boolean {
  return unit.status === "running" || unit.status === "planned";
}
