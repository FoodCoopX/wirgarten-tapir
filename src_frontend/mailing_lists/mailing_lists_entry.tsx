import { createRoot } from "react-dom/client";
import MailingListCard from "./MailingListCard.tsx";

const domNode = document.getElementById("mailing_lists_entry");
if (domNode) {
  const root = createRoot(domNode);

  root.render(<MailingListCard />);
} else {
  console.error("Failed to render mailing lists from React");
}
