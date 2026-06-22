import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import DeliveriesButton from "./DeliveriesButton.tsx";
import MemberDeleteButton from "./MemberDeleteButton.tsx";
import PaymentsButton from "./PaymentsButton.tsx";
import SubscriptionCancellationButton from "./SubscriptionCancellationButton.tsx";

const domNodeSubscriptionCancellationButton = document.getElementById(
  "subscription_cancellation_button",
);

if (domNodeSubscriptionCancellationButton) {
  const root = createRoot(domNodeSubscriptionCancellationButton);
  root.render(<SubscriptionCancellationButton csrfToken={getCsrfToken()} />);
} else {
  console.error("Cancellation button not found");
}

const domNodeMemberDeleteButton = document.getElementById(
  "member_delete_button",
);

if (domNodeMemberDeleteButton) {
  const root = createRoot(domNodeMemberDeleteButton);
  root.render(<MemberDeleteButton csrfToken={getCsrfToken()} />);
} else {
  console.error("Member delete button not found");
}

const domNodePaymentButton = document.getElementById("payments_button");

if (domNodePaymentButton) {
  const root = createRoot(domNodePaymentButton);
  root.render(<PaymentsButton csrfToken={getCsrfToken()} />);
} else {
  console.error("Member payments button not found");
}

const domNodeDeliveriesButton = document.getElementById("deliveries_button");

if (domNodeDeliveriesButton) {
  const root = createRoot(domNodeDeliveriesButton);
  root.render(<DeliveriesButton csrfToken={getCsrfToken()} />);
} else {
  console.error("Member deliveries button not found");
}
