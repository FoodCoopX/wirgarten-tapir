import { PublicSubscription } from "../api-client";

export default function formatSubscription(subscription: {
  quantity: number;
  product: { name: string };
}) {
  return subscription.quantity + " × " + subscription.product.name;
}

export function formatPublicSubscription(subscription: PublicSubscription) {
  return subscription.quantity + " × " + subscription.productName;
}
