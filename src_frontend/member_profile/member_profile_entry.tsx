import { createRoot } from "react-dom/client";
import DeliveryListCard from "./deliveries_and_jokers/DeliveryListCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionCancellationCard from "./subscription_cancellation/SubscriptionCancellationCard.tsx";
import SubscriptionCards from "./subscriptions/SubscriptionCards.tsx";
import MemberProfileWaitingListCard from "./waiting_list/MemberProfileWaitingListCard.tsx";
import FuturePaymentsCard from "./future_payments/FuturePaymentsCard.tsx";

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

const domNodeWaitingListCard = document.getElementById(
  "member_profile_waiting_list_entry",
);
if (domNodeWaitingListCard) {
  const root = createRoot(domNodeWaitingListCard);

  root.render(
    <MemberProfileWaitingListCard
      memberId={domNodeWaitingListCard.dataset.memberId!}
      adminEmail={domNodeWaitingListCard.dataset.adminEmail!}
    />,
  );
} else {
  console.error("Failed to render waiting list card from React");
}

const domNodeFuturePaymentsCard = document.getElementById(
  "future_payments_card",
);
if (domNodeFuturePaymentsCard) {
  const root = createRoot(domNodeFuturePaymentsCard);

  root.render(
    <FuturePaymentsCard
      memberId={domNodeFuturePaymentsCard.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error("Failed to render future payments card from React");
}
