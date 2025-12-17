import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionCancellationButton from "./SubscriptionCancellationButton.tsx";
import MemberDeleteButton from "./MemberDeleteButton.tsx";

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
