import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionCancellationButton from "./SubscriptionCancellationButton.tsx";

const domNodeSubscriptionCancellationButton = document.getElementById(
  "subscription_cancellation_button",
);

if (!domNodeSubscriptionCancellationButton) {
  console.error("Cancellation button not found");
} else {
  const root = createRoot(domNodeSubscriptionCancellationButton);
  root.render(<SubscriptionCancellationButton csrfToken={getCsrfToken()} />);
}
