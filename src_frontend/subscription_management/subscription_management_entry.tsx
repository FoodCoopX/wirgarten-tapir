import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionManagement from "./SubscriptionManagement.tsx";

const domNode = document.getElementById("subscription_management");
if (domNode) {
  createRoot(domNode).render(
    <SubscriptionManagement
      token={domNode.dataset.token!}
      csrfToken={getCsrfToken()}
    />,
  );
}
