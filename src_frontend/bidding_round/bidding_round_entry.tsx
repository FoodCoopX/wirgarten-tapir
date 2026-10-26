import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import BiddingRound from "./BiddingRound.tsx";

const domNode = document.getElementById("bidding_round-root");
if (domNode) {
  const root = createRoot(domNode);
  const skipIntro =
    new URLSearchParams(window.location.search).get("skip_intro") === "1";
  root.render(
    <BiddingRound csrfToken={getCsrfToken()} skipIntro={skipIntro} />,
  );
} else {
  console.error("Failed to render bidding_round from React");
}
