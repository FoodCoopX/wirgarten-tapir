import { createRoot } from "react-dom/client";
import DeliveryListCard from "./DeliveryListCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionCancellationButton from "./SubscriptionCancellationButton.tsx";

const domNode = document.getElementById("delivery_list_card");
if (domNode) {
  const deliveryListRoot = createRoot(domNode);

  deliveryListRoot.render(
    <DeliveryListCard
      memberId={domNode.dataset.memberId!}
      areJokersEnabled={domNode.dataset.jokersEnabled! == "true"}
      csrfToken={getCsrfToken()}
      pickupLocationModalUrl={domNode.dataset.pickupLocationModalUrl!}
    />,
  );
} else {
  console.error("Failed to render delivery list card from React");
}

for (const domNode of document.getElementsByClassName(
  "subscriptionCancellationButton",
) as HTMLCollectionOf<HTMLElement>) {
  const cancellationButtonRoot = createRoot(domNode);

  cancellationButtonRoot.render(
    <SubscriptionCancellationButton
      csrfToken={getCsrfToken()}
      memberId={domNode.dataset.memberId!}
      productTypeName={domNode.dataset.productTypeName!}
    />,
  );
}
