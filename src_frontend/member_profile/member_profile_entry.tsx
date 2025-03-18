import { createRoot } from "react-dom/client";
import DeliveryListCard from "./DeliveryListCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNode = document.getElementById("delivery_list_card");
if (domNode) {
  const root = createRoot(domNode);

  root.render(
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
