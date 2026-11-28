import { PublicSubscription } from "../api-client";
import { toApiDate } from "./apiDate.ts";

export function isSubscriptionActive(subscription: PublicSubscription) {
  const today = toApiDate(new Date());
  return (
    today >= subscription.startDate &&
    (!subscription.endDate || today <= subscription.endDate)
  );
}
