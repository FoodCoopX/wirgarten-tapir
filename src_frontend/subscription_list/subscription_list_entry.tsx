import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionChangeDatesButton from "./SubscriptionChangeDatesButton.tsx";
import SubscriptionChangePriceButton from "./SubscriptionChangePriceButton.tsx";

const domNodeSubscriptionChangeDatesButton = document.getElementById(
  "subscription_change_dates_button",
);

if (!domNodeSubscriptionChangeDatesButton) {
  console.error("Subscription change dates button not found");
} else {
  const root = createRoot(domNodeSubscriptionChangeDatesButton);
  root.render(<SubscriptionChangeDatesButton csrfToken={getCsrfToken()} />);
}

const domNodeSubscriptionChangePriceButton = document.getElementById(
  "subscription_change_price_button",
);

if (!domNodeSubscriptionChangePriceButton) {
  console.error("Subscription change price button not found");
} else {
  const root = createRoot(domNodeSubscriptionChangePriceButton);
  root.render(<SubscriptionChangePriceButton csrfToken={getCsrfToken()} />);
}
