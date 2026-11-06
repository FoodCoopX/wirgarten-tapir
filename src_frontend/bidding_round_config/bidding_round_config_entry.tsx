import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import BiddingRoundConfig from "./BiddingRoundConfig.tsx";

const domNode = document.getElementById("bidding_round-config-root");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<BiddingRoundConfig csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render bidding_round config from React");
}
