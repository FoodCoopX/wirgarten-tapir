import { createRoot } from "react-dom/client";
import CreditList from "./CreditList.tsx";

const domNode = document.getElementById("credit_list");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<CreditList />);
} else {
  console.error("Failed to render credit list from React");
}
