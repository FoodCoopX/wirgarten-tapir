import { createRoot } from "react-dom/client";
import DeliveryListCard from "./DeliveryListCard.tsx";

const domNode = document.getElementById("delivery_list_card");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<DeliveryListCard memberId={domNode.dataset.memberId!} />);
} else {
  console.error("Failed to render delivery list card from React");
}
