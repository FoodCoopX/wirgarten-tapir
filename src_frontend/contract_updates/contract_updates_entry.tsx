import { createRoot } from "react-dom/client";
import ContractUpdatesCard from "./ContractUpdatesCard.tsx";

const domNode = document.getElementById("contract_updates");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<ContractUpdatesCard />);
} else {
  console.error("Failed to render contract updates from React");
}
