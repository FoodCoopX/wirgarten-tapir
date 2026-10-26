import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import BiddingRoundResults from "./BiddingRoundResults.tsx";

const domNode = document.getElementById("bidding_round-results-root");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<BiddingRoundResults csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render bidding_round results from React");
}
