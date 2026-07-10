import { PublicSubscription, Subscription } from "../api-client";

export default function formatSubscription(subscription: Subscription) {
  return subscription.quantity + " × " + subscription.product.name;
}

export function formatPublicSubscription(subscription: PublicSubscription) {
  return subscription.quantity + " × " + subscription.productName;
}
