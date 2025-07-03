import { PublicSubscription } from "../api-client";

export function isSubscriptionActive(subscription: PublicSubscription) {
  const now = new Date();
  return (
    now >= subscription.startDate &&
    (!subscription.endDate || now <= subscription.endDate)
  );
}
