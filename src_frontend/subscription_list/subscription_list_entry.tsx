import { createRoot } from "react-dom/client";
import AdminSubscriptionAdditionButton from "./AdminSubscriptionAdditionButton.tsx";
import AdminSubscriptionChangeButton from "./AdminSubscriptionChangeButton.tsx";
import SubscriptionChangeDatesButton from "./SubscriptionChangeDatesButton.tsx";
import SubscriptionChangePriceButton from "./SubscriptionChangePriceButton.tsx";
import SubscriptionTrialPeriodButton from "./SubscriptionTrialPeriodButton.tsx";

const domNodeSubscriptionChangeDatesButton = document.getElementById(
  "subscription_change_dates_button",
);

if (!domNodeSubscriptionChangeDatesButton) {
  console.error("Subscription change dates button not found");
} else {
  const root = createRoot(domNodeSubscriptionChangeDatesButton);
  root.render(<SubscriptionChangeDatesButton />);
}

const domNodeSubscriptionChangePriceButton = document.getElementById(
  "subscription_change_price_button",
);

if (!domNodeSubscriptionChangePriceButton) {
  console.error("Subscription change price button not found");
} else {
  const root = createRoot(domNodeSubscriptionChangePriceButton);
  root.render(<SubscriptionChangePriceButton />);
}

const domNodeSubscriptionTrialPeriodButton = document.getElementById(
  "subscription_trial_period_button",
);

if (domNodeSubscriptionTrialPeriodButton) {
  const root = createRoot(domNodeSubscriptionTrialPeriodButton);
  root.render(<SubscriptionTrialPeriodButton />);
}

const domNodeAdminSubscriptionChangeButton = document.getElementById(
  "admin_subscription_change_button",
);

if (domNodeAdminSubscriptionChangeButton) {
  const root = createRoot(domNodeAdminSubscriptionChangeButton);
  root.render(<AdminSubscriptionChangeButton />);
}

const domNodeAdminSubscriptionAdditionButton = document.getElementById(
  "admin_subscription_addition_button",
);

if (domNodeAdminSubscriptionAdditionButton) {
  const root = createRoot(domNodeAdminSubscriptionAdditionButton);
  root.render(<AdminSubscriptionAdditionButton />);
}
