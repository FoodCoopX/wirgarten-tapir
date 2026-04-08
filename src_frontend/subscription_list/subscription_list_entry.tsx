import { createRoot } from "react-dom/client";
import SubscriptionChangeDatesButton from "./SubscriptionChangeDatesButton.tsx";
import SubscriptionAddContractButton from "./SubscriptionAddContractButton.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNodeSubscriptionChangeDatesButton = document.getElementById(
  "subscription_change_dates_button",
);
const domNodeSubscriptionAddContractButton = document.getElementById(
    "subscription_add_contract_button",
);

if (!domNodeSubscriptionChangeDatesButton) {
  console.error("Subscription change dates button not found");
} else {
  const root = createRoot(domNodeSubscriptionChangeDatesButton);
  root.render(<SubscriptionChangeDatesButton csrfToken={getCsrfToken()} />);
}

if (!domNodeSubscriptionAddContractButton) {
  console.error("Subscription add contract button not found");
} else {
  const root = createRoot(domNodeSubscriptionAddContractButton);
  root.render(<SubscriptionAddContractButton csrfToken={getCsrfToken()} />);
}
