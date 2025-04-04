import { createRoot } from "react-dom/client";
import DeliveryListCard from "./deliveries_and_jokers/DeliveryListCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionCancellationCard from "./subscription_cancellation/SubscriptionCancellationCard.tsx";

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
