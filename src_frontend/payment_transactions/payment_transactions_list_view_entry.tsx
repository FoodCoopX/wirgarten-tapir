import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import PaymentTransactionsBase from "./PaymentTransactionsBase.tsx";

const domNode = document.getElementById("payment_transactions");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<PaymentTransactionsBase csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render payment transactions from React");
}
