import { Subscription } from "../api-client";

export default function formatSubscription(subscription: Subscription) {
  return subscription.quantity + " × " + subscription.product.name;
}
