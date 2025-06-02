import { createRoot } from "react-dom/client";
import ContractUpdatesCard from "./ContractUpdatesCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNode = document.getElementById("contract_updates");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<ContractUpdatesCard csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render contract updates from React");
}
