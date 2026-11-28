import { createRoot } from "react-dom/client";
import PaymentTransactionsBase from "./PaymentTransactionsBase.tsx";

const domNode = document.getElementById("payment_transactions");
if (domNode) {
  const root = createRoot(domNode);
  root.render(
    <PaymentTransactionsBase
      paymentExportExclusionEnabled={
        domNode.dataset.paymentExportExclusionEnabled === "True"
      }
    />,
  );
} else {
  console.error("Failed to render payment transactions from React");
}
