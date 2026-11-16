import { createRoot } from "react-dom/client";

import { getCsrfToken } from "../utils/getCsrfToken.ts";
import BiddingRound from "./BiddingRound.tsx";

const domNode = document.getElementById("bidding_round-root");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<BiddingRound csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render bidding_round from React");
}
