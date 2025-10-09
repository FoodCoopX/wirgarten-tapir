import { createRoot } from "react-dom/client";
import SubscriptionChangeDatesButton from "./SubscriptionChangeDatesButton.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNodeSubscriptionChangeDatesButton = document.getElementById(
  "subscription_change_dates_button",
);

if (!domNodeSubscriptionChangeDatesButton) {
  console.error("Subscription change dates button not found");
} else {
  const root = createRoot(domNodeSubscriptionChangeDatesButton);
  root.render(<SubscriptionChangeDatesButton csrfToken={getCsrfToken()} />);
}
