import { createRoot } from "react-dom/client";
import WaitingListCard from "./WaitingListCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNode = document.getElementById("waiting_list");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<WaitingListCard csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render waiting list from React");
}
