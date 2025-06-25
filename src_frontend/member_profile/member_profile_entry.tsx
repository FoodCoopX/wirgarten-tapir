import { createRoot } from "react-dom/client";
import DeliveryListCard from "./deliveries_and_jokers/DeliveryListCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionCancellationCard from "./subscription_cancellation/SubscriptionCancellationCard.tsx";
import SubscriptionCards from "./subscriptions/SubscriptionCards.tsx";

const domNodeDeliveryListCard = document.getElementById("delivery_list_card");
if (domNodeDeliveryListCard) {
  const root = createRoot(domNodeDeliveryListCard);

  root.render(
    <DeliveryListCard
      memberId={domNodeDeliveryListCard.dataset.memberId!}
      areJokersEnabled={
        domNodeDeliveryListCard.dataset.jokersEnabled! == "true"
      }
      csrfToken={getCsrfToken()}
      pickupLocationModalUrl={
        domNodeDeliveryListCard.dataset.pickupLocationModalUrl!
      }
    />,
  );
} else {
  console.error("Failed to render delivery list card from React");
}

const domNodeSubscriptionCancellationCard = document.getElementById(
  "subscription_cancellation_card",
);
if (domNodeSubscriptionCancellationCard) {
  // Element is absent if Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL is turned off.
  const root = createRoot(domNodeSubscriptionCancellationCard);

  root.render(
    <SubscriptionCancellationCard
      memberId={domNodeSubscriptionCancellationCard.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
}

const subscriptionCards = document.getElementById("subscription_cards");
if (subscriptionCards) {
  const root = createRoot(subscriptionCards);

  root.render(
    <SubscriptionCards
      memberId={subscriptionCards.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error("Failed to render subscription cards from React");
}
