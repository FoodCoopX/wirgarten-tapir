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
    />,
  );
} else {
  console.error("Failed to render delivery list card from React");
}

const contractTilesElement = document.getElementById("contract-tiles");
if (contractTilesElement) {
  const root = createRoot(contractTilesElement);
  const showCancellationCard =
    contractTilesElement.dataset.showCancellationCard;
  if (showCancellationCard) {
    root.render(
      <>
        <SubscriptionCards
          memberId={contractTilesElement.dataset.memberId!}
          csrfToken={getCsrfToken()}
        />
        <SubscriptionCancellationCard
          memberId={contractTilesElement.dataset.memberId!}
          csrfToken={getCsrfToken()}
        />
      </>,
    );
  } else {
    root.render(
      <>
        <SubscriptionCards
          memberId={contractTilesElement.dataset.memberId!}
          csrfToken={getCsrfToken()}
        />
      </>,
    );
  }
}
