import { createRoot } from "react-dom/client";
import NewContractCancellationsCard from "./NewContractCancellationsCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNode = document.getElementById("new_contract_cancellations");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<NewContractCancellationsCard csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render cancellations from React");
}
